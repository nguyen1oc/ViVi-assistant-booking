from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
import uuid
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from src.database import Database
from src.services.booking.common import parse_utc
from src.services.profile.models import BookingSignalCandidate, ProfileSnapshot, SignalCandidate
from src.services.profile.taxonomy import normalize_key

logger = logging.getLogger("profile.lifecycle")
VIETNAM_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _legacy_policy_interest(value: str) -> dict[str, str]:
    """Convert a pre-structured policy interest into the current list item shape."""
    model_match = re.search(r"\bVF\s*(\d+)\b", value, re.IGNORECASE)
    vehicle_model = f"VF {model_match.group(1)}" if model_match else "unknown"
    topic = "maintenance" if "bảo dưỡng" in value.casefold() else value
    return {"topic": topic, "vehicle_model": vehicle_model}


def _merge_list_values(key: str, old_value: Any, new_value: list[Any]) -> list[Any]:
    """Append list values in stable order and remove structurally identical entries."""
    old_items = old_value if isinstance(old_value, list) else ([] if old_value is None else [old_value])
    if key == "policy_interest":
        old_items = [
            _legacy_policy_interest(item.strip()) if isinstance(item, str) and item.strip() else item
            for item in old_items
        ]
    merged: list[Any] = []
    seen: set[str] = set()
    for item in [*old_items, *new_value]:
        try:
            identity = json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
        except (TypeError, ValueError):
            identity = repr(item)
        if identity not in seen:
            seen.add(identity)
            merged.append(item)
    return merged


def _booking_time_vietnam(value: str) -> str:
    """Expose booking time to agents in the application's Vietnam timezone."""
    return parse_utc(value).astimezone(VIETNAM_TZ).isoformat()


class ProfileService:
    def __init__(self, database: Database, *, identity_secret: str) -> None:
        self.db = database
        self.identity_secret = identity_secret.encode("utf-8")

    def _hash(self, kind: str, value: str) -> str:
        normalized = value.strip().casefold() if kind == "email" else "".join(c for c in value if c.isdigit())
        return hmac.new(self.identity_secret, f"{kind}:{normalized}".encode(), hashlib.sha256).hexdigest()

    def _canonical(self, c, profile_id: str) -> str:
        seen: set[str] = set()
        while profile_id and profile_id not in seen:
            seen.add(profile_id)
            row = c.execute("SELECT state,merged_into_profile_id FROM user_profiles WHERE id=?", (profile_id,)).fetchone()
            if not row or row["state"] != "merged" or not row["merged_into_profile_id"]:
                return profile_id
            profile_id = row["merged_into_profile_id"]
        return profile_id

    def resolve_or_create(self, conversation_id: str, anon_session_id: str = "") -> ProfileSnapshot:
        now = _now()
        with self.db.transaction(immediate=True) as c:
            profile_id = None
            for typ, value in (("conversation", conversation_id), ("anon_session", anon_session_id)):
                if not value or value == "unknown":
                    continue
                row = c.execute("SELECT profile_id FROM user_profile_identities WHERE identity_type=? AND identity_value=?", (typ, value)).fetchone()
                if row:
                    candidate_id = self._canonical(c, row["profile_id"])
                    candidate = c.execute("SELECT state FROM user_profiles WHERE id=?", (candidate_id,)).fetchone()
                    # An anonymous browser cookie is correlation, not authentication.
                    # Never let it silently re-open a trusted profile in a brand-new thread.
                    if typ == "anon_session" and candidate and candidate["state"] == "trusted":
                        continue
                    profile_id = candidate_id
                    break
            if not profile_id:
                profile_id = _id("profile")
                c.execute("INSERT INTO user_profiles(id,state,version,created_at,updated_at,last_seen_at) VALUES(?,'anonymous',1,?,?,?)", (profile_id, now, now, now))
            for typ, value in (("conversation", conversation_id), ("anon_session", anon_session_id)):
                if value and value != "unknown":
                    existing = c.execute("SELECT profile_id FROM user_profile_identities WHERE identity_type=? AND identity_value=?", (typ, value)).fetchone()
                    if not existing:
                        c.execute("INSERT INTO user_profile_identities VALUES(?,?,?,?,?,?,?,?)", (_id("identity"), profile_id, typ, value, "anonymous", "chat", now, now))
            c.execute("UPDATE user_profiles SET last_seen_at=?,updated_at=? WHERE id=?", (now, now, profile_id))
        return self.load(profile_id)

    def load(self, profile_id: str) -> ProfileSnapshot:
        with self.db.connect() as c:
            profile_id = self._canonical(c, profile_id)
            profile = c.execute("SELECT id,state,version FROM user_profiles WHERE id=?", (profile_id,)).fetchone()
            rows = c.execute("SELECT category,key,value_json,description,certainty,confidence,source_type,source_ref,observed_at FROM user_profile_signals WHERE profile_id=? AND status='active' ORDER BY observed_at DESC", (profile_id,)).fetchall()
        snapshot = ProfileSnapshot(id=profile["id"], state=profile["state"], version=profile["version"], signals=[{**dict(row), "value": json.loads(row["value_json"])} for row in rows])
        logger.info("profile.loaded profile_id=%s state=%s version=%s signal_count=%s",
                    snapshot.id, snapshot.state, snapshot.version, len(snapshot.signals))
        return snapshot

    def load_for_user(self, user_id: str) -> ProfileSnapshot:
        """Load a canonical profile by profile ID or authenticated person ID."""
        with self.db.connect() as c:
            if user_id.startswith("profile_"):
                row = c.execute("SELECT id FROM user_profiles WHERE id=?", (user_id,)).fetchone()
                profile_id = str(row["id"]) if row else ""
            else:
                row = c.execute(
                    "SELECT profile_id FROM user_profile_identities "
                    "WHERE identity_type='person' AND identity_value=? ORDER BY last_seen_at DESC LIMIT 1",
                    (user_id,),
                ).fetchone()
                profile_id = str(row["profile_id"]) if row else ""
        if not profile_id:
            raise KeyError(user_id)
        return self.load(profile_id)

    def bind_person_conversation(
        self,
        conversation_id: str,
        *,
        person_id: str,
        email: str,
        phone: str = "",
        source: str,
        trace_id: str = "",
    ) -> ProfileSnapshot:
        """Bind a server-authenticated conversation to one person's canonical profile."""
        current = self.resolve_or_create(conversation_id)
        return self.promote_identity(
            current.id,
            person_id=person_id,
            email=email,
            phone=phone,
            source=source,
            trace_id=trace_id,
        )

    def resolve_booking_other_participant_profile(self, booking_id: str, speaker_role: str) -> ProfileSnapshot:
        """Resolve the other booking participant from trusted booking data."""
        if speaker_role not in {"booker", "driver"}:
            raise KeyError(booking_id)
        with self.db.connect() as c:
            row = c.execute(
                "SELECT b.booker_person_id,b.driver_person_id,booker.email booker_email,"
                "booker.normalized_email booker_normalized_email,booker.phone booker_phone,"
                "booker.normalized_phone booker_normalized_phone,driver.email driver_email,"
                "driver.normalized_email driver_normalized_email,driver.phone driver_phone,"
                "driver.normalized_phone driver_normalized_phone "
                "FROM bookings b LEFT JOIN people booker ON booker.id=b.booker_person_id "
                "LEFT JOIN people driver ON driver.id=b.driver_person_id WHERE b.id=?",
                (booking_id,),
            ).fetchone()
        if not row:
            raise KeyError(booking_id)
        target_role = "driver" if speaker_role == "booker" else "booker"
        target_person_id = row[f"{target_role}_person_id"]
        speaker_person_id = row[f"{speaker_role}_person_id"]
        if not target_person_id or target_person_id == speaker_person_id:
            raise KeyError(booking_id)
        email = str(row[f"{target_role}_normalized_email"] or row[f"{target_role}_email"] or "").strip().casefold()
        if not email:
            raise KeyError(booking_id)
        return self.promote_identity(
            None,
            person_id=str(target_person_id),
            email=email,
            phone=str(row[f"{target_role}_normalized_phone"] or row[f"{target_role}_phone"] or ""),
            source=f"{speaker_role}_third_party_report",
        )

    def apply(self, profile_id: str, candidates: list[SignalCandidate], *, source_ref: str, trace_id: str = "") -> ProfileSnapshot:
        before = self.load(profile_id)
        logger.info("profile.update.before trace_id=%s profile_id=%s snapshot=%s", trace_id, profile_id, before.model_dump())
        now = _now()
        operations: list[dict[str, Any]] = []
        with self.db.transaction(immediate=True) as c:
            profile_id = self._canonical(c, profile_id)
            for candidate in candidates:
                # Candidate validation owns category acceptance. Do not silently
                # relabel an invalid model category as custom_intent here.
                category = candidate.category
                key = normalize_key(candidate.key) or "unspecified"
                old = c.execute("SELECT id,value_json,confidence,certainty,source_type FROM user_profile_signals WHERE profile_id=? AND category=? AND key=? AND status='active' ORDER BY observed_at DESC LIMIT 1", (profile_id, category, key)).fetchone()
                if old and old["source_type"] == "explicit_user" and candidate.source_type == "implicit_user":
                    operations.append({"operation": "ignored_lower_precedence", "category": category, "key": key, "candidate": candidate.model_dump()})
                    continue
                if candidate.operation == "retract":
                    if old:
                        c.execute("UPDATE user_profile_signals SET status='retracted',updated_at=? WHERE id=?", (now, old["id"]))
                    operations.append({"operation": "retract", "category": category, "key": key})
                    continue
                signal_id = _id("signal")
                confidence = candidate.confidence
                if old and candidate.operation == "strengthen":
                    confidence = max(confidence, min(1.0, float(old["confidence"] or 0.5) + 0.15))
                elif old and candidate.operation == "weaken":
                    confidence = min(confidence, max(0.0, float(old["confidence"] or 0.5) - 0.25))
                value = candidate.value
                if old and isinstance(value, list) and candidate.operation in {"add", "strengthen"}:
                    value = _merge_list_values(key, json.loads(old["value_json"]), value)
                    candidate = candidate.model_copy(update={"value": value})
                c.execute("INSERT INTO user_profile_signals VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (signal_id, profile_id, category, key, json.dumps(value, ensure_ascii=False), candidate.description, candidate.certainty, confidence, candidate.source_type, source_ref, now, "active", None, now, now))
                if old:
                    c.execute("UPDATE user_profile_signals SET status='superseded',superseded_by_signal_id=?,updated_at=? WHERE id=?", (signal_id, now, old["id"]))
                operations.append({**candidate.model_dump(), "category": category, "key": key, "confidence": confidence})
            c.execute("UPDATE user_profiles SET version=version+1,updated_at=?,last_seen_at=? WHERE id=?", (now, now, profile_id))
        logger.info("profile.update.operations trace_id=%s profile_id=%s operations=%s", trace_id, profile_id, operations)
        after = self.load(profile_id)
        logger.info("profile.update.after trace_id=%s profile_id=%s snapshot=%s", trace_id, profile_id, after.model_dump())
        return after

    def promote_from_booking(self, profile_id: str | None, booking_id: str, *, source: str, trace_id: str = "") -> ProfileSnapshot | None:
        with self.db.connect() as c:
            row = c.execute("SELECT b.booker_person_id,COALESCE(p.normalized_email,lower(p.email)) normalized_email,COALESCE(p.normalized_phone,p.phone) normalized_phone FROM bookings b JOIN people p ON p.id=b.booker_person_id WHERE b.id=?", (booking_id,)).fetchone()
        if not row or not row["normalized_email"]:
            return self.load(profile_id) if profile_id else None
        return self.promote_identity(profile_id, person_id=row["booker_person_id"], email=row["normalized_email"], phone=row["normalized_phone"] or "", source=source, trace_id=trace_id)

    def promote_identity(self, profile_id: str | None, *, person_id: str, email: str, phone: str = "", source: str, trace_id: str = "") -> ProfileSnapshot:
        email_hash = self._hash("email", email)
        phone_hash = self._hash("phone", phone) if phone else ""
        now = _now()
        with self.db.transaction(immediate=True) as c:
            target_row = c.execute("SELECT profile_id FROM user_profile_identities WHERE identity_type='email_hash' AND identity_value=?", (email_hash,)).fetchone()
            target = self._canonical(c, target_row["profile_id"]) if target_row else None
            if profile_id:
                profile_id = self._canonical(c, profile_id)
            if not profile_id:
                profile_id = _id("profile")
                c.execute("INSERT INTO user_profiles(id,state,version,created_at,updated_at,last_seen_at) VALUES(?,'trusted',1,?,?,?)", (profile_id, now, now, now))
            canonical = target or profile_id
            logger.info("profile.merge.decision trace_id=%s source=%s current=%s email_target=%s canonical=%s", trace_id, source, profile_id, target, canonical)
            if target and profile_id != target:
                self._merge(c, profile_id, target, now)
            else:
                c.execute("UPDATE user_profiles SET state='trusted',updated_at=?,last_seen_at=? WHERE id=?", (now, now, canonical))
            aliases = [("email_hash", email_hash), ("person", person_id)]
            if phone_hash:
                aliases.append(("phone_hash", phone_hash))
            for typ, value in aliases:
                existing = c.execute("SELECT profile_id FROM user_profile_identities WHERE identity_type=? AND identity_value=?", (typ, value)).fetchone()
                if existing and typ == "phone_hash":
                    other = self._canonical(c, existing["profile_id"])
                    if other != canonical:
                        self._merge(c, other, canonical, now)
                if not existing:
                    c.execute("INSERT INTO user_profile_identities VALUES(?,?,?,?,?,?,?,?)", (_id("identity"), canonical, typ, value, "trusted", source, now, now))
            logger.info("profile.merge.result trace_id=%s source=%s canonical=%s", trace_id, source, canonical)
        return self.load(canonical)

    def _merge(self, c, source: str, target: str, now: str) -> None:
        # Email-selected target wins. Preserve all aliases and signal provenance.
        c.execute("UPDATE user_profile_identities SET profile_id=?,last_seen_at=? WHERE profile_id=?", (target, now, source))
        rows = c.execute("SELECT id,category,key FROM user_profile_signals WHERE profile_id=? AND status='active'", (source,)).fetchall()
        for row in rows:
            existing = c.execute("SELECT id FROM user_profile_signals WHERE profile_id=? AND category=? AND key=? AND status='active' ORDER BY observed_at DESC LIMIT 1", (target, row["category"], row["key"])).fetchone()
            if existing:
                c.execute("UPDATE user_profile_signals SET status='superseded',superseded_by_signal_id=?,updated_at=? WHERE id=?", (existing["id"], now, row["id"]))
            else:
                c.execute("UPDATE user_profile_signals SET profile_id=?,updated_at=? WHERE id=?", (target, now, row["id"]))
        c.execute("UPDATE user_profiles SET state='merged',merged_into_profile_id=?,updated_at=? WHERE id=?", (target, now, source))
        c.execute("UPDATE user_profiles SET state='trusted',version=version+1,updated_at=?,last_seen_at=? WHERE id=?", (now, now, target))

    def booking_context(self, booking_id: str) -> dict[str, Any]:
        with self.db.connect() as c:
            row = c.execute("SELECT b.id,b.status,t.start_at,m.code model_code,m.name vehicle_model,s.id showroom_id,s.name showroom_name FROM bookings b JOIN test_drive_slots t ON t.id=b.slot_id JOIN demo_vehicles d ON d.id=t.demo_vehicle_id JOIN vehicle_variants v ON v.id=d.variant_id JOIN vehicle_models m ON m.id=v.model_id JOIN showrooms s ON s.id=t.showroom_id WHERE b.id=?", (booking_id,)).fetchone()
        context = dict(row) if row else {}
        if context.get("start_at"):
            context["start_at"] = _booking_time_vietnam(str(context["start_at"]))
            context["timezone"] = "UTC+7"
        return context

    def booking_participants_context(self, booking_id: str) -> dict[str, Any]:
        """Return participant identities for an authenticated booking participant.

        This is intentionally separate from ``booking_context``: ordinary advisory
        flows do not need contact data, while a driver-invitation link is already
        authenticated for this exact booking.
        """
        with self.db.connect() as c:
            row = c.execute(
                "SELECT bp.full_name booker_name,bp.email booker_email,"
                "dp.full_name driver_name,dp.email driver_email "
                "FROM bookings b "
                "LEFT JOIN people bp ON bp.id=b.booker_person_id "
                "LEFT JOIN people dp ON dp.id=b.driver_person_id "
                "WHERE b.id=?",
                (booking_id,),
            ).fetchone()
        if not row:
            return {}
        return {
            "booker": {
                "name": str(row["booker_name"] or ""),
                "email": str(row["booker_email"] or ""),
            },
            "driver": {
                "name": str(row["driver_name"] or ""),
                "email": str(row["driver_email"] or ""),
            },
        }

    def latest_booking_context(self, profile_id: str) -> dict[str, Any]:
        with self.db.connect() as c:
            profile_id = self._canonical(c, profile_id)
            row = c.execute("SELECT b.id FROM user_profile_identities i JOIN bookings b ON b.booker_person_id=i.identity_value WHERE i.profile_id=? AND i.identity_type='person' AND b.status IN ('confirmed','checked_in','completed') ORDER BY b.confirmed_at DESC LIMIT 1", (profile_id,)).fetchone()
        if not row:
            return {"active": False}
        context = self.booking_context(row["id"])
        return {"active": context.get("status") in {"confirmed", "checked_in"}, **context}

    def booking_profiles_context(self, booking_id: str) -> dict[str, Any]:
        """Build person-scoped profile inputs for a booking sales brief."""
        with self.db.connect() as c:
            row = c.execute(
                "SELECT b.status,b.booker_person_id,b.driver_person_id,t.start_at,"
                "m.name vehicle_model,s.name showroom_name,bp.full_name booker_name,dp.full_name driver_name "
                "FROM bookings b JOIN test_drive_slots t ON t.id=b.slot_id "
                "JOIN demo_vehicles d ON d.id=t.demo_vehicle_id "
                "JOIN vehicle_variants v ON v.id=d.variant_id JOIN vehicle_models m ON m.id=v.model_id "
                "JOIN showrooms s ON s.id=t.showroom_id "
                "LEFT JOIN people bp ON bp.id=b.booker_person_id LEFT JOIN people dp ON dp.id=b.driver_person_id "
                "WHERE b.id=?",
                (booking_id,),
            ).fetchone()
        if not row:
            raise KeyError(booking_id)

        def participant(person_id: str | None, name: str, role: str) -> dict[str, Any]:
            data: dict[str, Any] = {"role": role, "name": name, "profile_available": False}
            if not person_id:
                return data
            try:
                snapshot = self.load_for_user(person_id)
            except KeyError:
                return data
            from src.services.profile.context import build_profile_context
            return {**data, "profile_available": True, "profile": build_profile_context(snapshot)}

        same_person = bool(row["booker_person_id"] and row["booker_person_id"] == row["driver_person_id"])
        result = {
            "booking": {
                "status": row["status"],
                "start_at": _booking_time_vietnam(str(row["start_at"])),
                "timezone": "UTC+7",
                "vehicle_model": row["vehicle_model"], "showroom_name": row["showroom_name"],
            },
            "same_person": same_person,
            "booker": participant(row["booker_person_id"], str(row["booker_name"] or ""), "booker"),
        }
        if not same_person:
            result["driver"] = participant(row["driver_person_id"], str(row["driver_name"] or ""), "driver")
        return result

    def booking_context_signals(self, booking_id: str) -> list[dict[str, Any]]:
        with self.db.connect() as c:
            rows = c.execute(
                "SELECT category,key,value_json,description,subject,certainty,confidence,source_type,source_participant "
                "FROM test_drive_context_signals WHERE booking_id=? AND status='active' ORDER BY updated_at DESC",
                (booking_id,),
            ).fetchall()
        return [{**dict(row), "value": json.loads(row["value_json"])} for row in rows]

    def participant_context(self, booking_id: str, role: str) -> dict[str, Any]:
        """Project active booking signals into a stable prompt-facing view."""
        signals = self.booking_context_signals(booking_id)
        with self.db.connect() as c:
            booking = c.execute(
                "SELECT booker_person_id,driver_person_id FROM bookings WHERE id=?", (booking_id,)
            ).fetchone()
        values = {(item["subject"], item["key"]): item["value"] for item in signals}
        own = role if role in {"booker", "driver"} else "booker"
        other = "driver" if own == "booker" else "booker"
        same_person = bool(booking and booking["booker_person_id"] and booking["booker_person_id"] == booking["driver_person_id"])
        participation = {
            "attending": values.get((own, f"{own}_attending"), "unknown"),
            "will_drive": values.get((own, f"{own}_will_drive"), "unknown"),
            "evaluation_involvement": values.get((own, f"{own}_evaluation_involvement"), "unknown"),
            "purchase_involvement": values.get((own, f"{own}_purchase_involvement"), "unknown"),
        }
        other_participant = {"role": other, "attending": values.get((other, f"{other}_attending"), "unknown")}
        guests = {
            "count": values.get(("group", "additional_guest_count"), "unknown"),
            "context": values.get(("group", "additional_guest_context"), []),
        }
        participant_roles = ["booker"] if same_person else ["booker", "driver"]
        missing = [
            f"{participant}_{field}"
            for participant in participant_roles
            for field in ("attending", "will_drive", "evaluation_involvement", "purchase_involvement")
            if values.get((participant, f"{participant}_{field}"), "unknown") == "unknown"
        ]
        if guests["count"] == "unknown":
            missing.append("additional_guest_count")
        known = {"booker_attending", "driver_attending", "booker_will_drive", "driver_will_drive", "booker_evaluation_involvement", "driver_evaluation_involvement", "booker_purchase_involvement", "driver_purchase_involvement", "additional_guest_count", "additional_guest_context"}
        return {"role": own, "booking_id": booking_id, "same_person": same_person, "booking_participation": participation,
                "other_participant": other_participant, "additional_attendees": guests,
                "participant_discovery_missing": missing,
                "other_booking_context": [item for item in signals if item["key"] not in known]}

    def apply_booking_signals(self, booking_id: str, candidates: list[BookingSignalCandidate], *, source_participant: str, source_ref: str) -> None:
        now = _now()
        with self.db.transaction(immediate=True) as c:
            for candidate in candidates:
                old = c.execute(
                    "SELECT id,source_type,source_participant,confidence FROM test_drive_context_signals "
                    "WHERE booking_id=? AND subject=? AND category=? AND key=? AND status='active' ORDER BY updated_at DESC LIMIT 1",
                    (booking_id, candidate.subject, candidate.category, candidate.key),
                ).fetchone()
                # A subject's explicit statement outranks a third-party inference/system default.
                self_report = candidate.subject == source_participant and candidate.source_type == "explicit_user"
                old_self_report = bool(old and old["source_participant"] == candidate.subject and old["source_type"] == "explicit_user")
                if old_self_report and not self_report:
                    continue
                if candidate.operation == "retract":
                    if old:
                        c.execute("UPDATE test_drive_context_signals SET status='retracted',updated_at=? WHERE id=?", (now, old["id"]))
                    continue
                value = candidate.value
                if old and isinstance(value, list) and candidate.operation in {"add", "strengthen"}:
                    value = _merge_list_values(candidate.key, json.loads(old["value_json"]), value)
                    candidate = candidate.model_copy(update={"value": value})
                signal_id = _id("booking_signal")
                confidence = candidate.confidence
                if old and candidate.operation == "strengthen":
                    confidence = max(confidence, min(1.0, float(old["confidence"] or .5) + .15))
                if old and candidate.operation == "weaken":
                    confidence = min(confidence, max(0.0, float(old["confidence"] or .5) - .25))
                c.execute("INSERT INTO test_drive_context_signals VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                    signal_id, booking_id, candidate.category, candidate.key, json.dumps(value, ensure_ascii=False),
                    candidate.description, candidate.subject, candidate.certainty, confidence, candidate.source_type,
                    source_participant, source_ref, "active", None, now, now,
                ))
                if old:
                    c.execute("UPDATE test_drive_context_signals SET status='superseded',superseded_by_signal_id=?,updated_at=? WHERE id=?", (signal_id, now, old["id"]))
            # A booking context change makes any generated portal brief stale.
            c.execute("DELETE FROM booking_profile_summaries WHERE booking_id=?", (booking_id,))

    def invalidate_booking_profile_summary(self, booking_id: str) -> None:
        with self.db.transaction(immediate=True) as c:
            c.execute("DELETE FROM booking_profile_summaries WHERE booking_id=?", (booking_id,))

    def booking_profile_summary(self, booking_id: str) -> dict[str, str] | None:
        """Return the latest stored sales brief for a booking, if one exists."""
        with self.db.connect() as c:
            row = c.execute(
                "SELECT summary_markdown,generated_at FROM booking_profile_summaries WHERE booking_id=?",
                (booking_id,),
            ).fetchone()
        if not row:
            return None
        return {"summary": str(row["summary_markdown"]), "generated_at": str(row["generated_at"])}

    def booking_profile_summary_is_current(self, booking_id: str, generated_at: str) -> bool:
        """Check whether a cached brief is newer than every factual source it uses."""
        with self.db.connect() as c:
            row = c.execute(
                """SELECT MAX(source_updated_at) source_updated_at FROM (
                SELECT b.updated_at source_updated_at FROM bookings b WHERE b.id=?
                UNION ALL
                SELECT s.updated_at FROM test_drive_context_signals s
                WHERE s.booking_id=? AND s.status='active'
                UNION ALL
                SELECT ps.updated_at FROM bookings b
                JOIN user_profile_identities i
                  ON i.identity_type='person'
                 AND i.identity_value IN (b.booker_person_id,b.driver_person_id)
                JOIN user_profile_signals ps ON ps.profile_id=i.profile_id
                WHERE b.id=? AND ps.status='active'
                ) AS sources""",
                (booking_id, booking_id, booking_id),
            ).fetchone()
        source_updated_at = str(row["source_updated_at"] or "") if row else ""
        return not source_updated_at or generated_at >= source_updated_at
    def save_booking_profile_summary(self, booking_id: str, summary: str) -> dict[str, str]:
        """Persist the newest generated sales brief for a booking."""
        now = _now()
        with self.db.transaction(immediate=True) as c:
            c.execute(
                """INSERT INTO booking_profile_summaries(booking_id,summary_markdown,generated_at,updated_at)
                VALUES(?,?,?,?)
                ON CONFLICT(booking_id) DO UPDATE SET summary_markdown=excluded.summary_markdown,
                generated_at=excluded.generated_at,updated_at=excluded.updated_at""",
                (booking_id, summary, now, now),
            )
        return {"summary": summary, "generated_at": now}

    def mock_debug_view(self, profile_id: str) -> dict[str, Any]:
        """Return a non-production diagnostic view of one profile and its history."""
        with self.db.connect() as c:
            requested = c.execute(
                "SELECT id,state,merged_into_profile_id,version,created_at,updated_at,last_seen_at "
                "FROM user_profiles WHERE id=?",
                (profile_id,),
            ).fetchone()
            if not requested:
                raise KeyError(profile_id)

            canonical_id = self._canonical(c, profile_id)
            lineage_ids = [canonical_id]
            pending = [canonical_id]
            while pending:
                parent_id = pending.pop()
                children = c.execute(
                    "SELECT id FROM user_profiles WHERE merged_into_profile_id=?",
                    (parent_id,),
                ).fetchall()
                for child in children:
                    child_id = str(child["id"])
                    if child_id not in lineage_ids:
                        lineage_ids.append(child_id)
                        pending.append(child_id)

            lineage = []
            signals = []
            for lineage_id in lineage_ids:
                row = c.execute(
                    "SELECT id,state,merged_into_profile_id,version,created_at,updated_at,last_seen_at "
                    "FROM user_profiles WHERE id=?",
                    (lineage_id,),
                ).fetchone()
                if row:
                    lineage.append(dict(row))
                rows = c.execute(
                    "SELECT id,profile_id,category,key,value_json,description,certainty,confidence,"
                    "source_type,source_ref,observed_at,status,superseded_by_signal_id,created_at,updated_at "
                    "FROM user_profile_signals WHERE profile_id=? ORDER BY observed_at DESC",
                    (lineage_id,),
                ).fetchall()
                for signal in rows:
                    item = dict(signal)
                    try:
                        item["value"] = json.loads(item["value_json"])
                    except (TypeError, json.JSONDecodeError):
                        item["value"] = item["value_json"]
                    signals.append(item)

            identities = [
                dict(row)
                for row in c.execute(
                    "SELECT id,profile_id,identity_type,identity_value,trust_level,source,created_at,last_seen_at "
                    "FROM user_profile_identities WHERE profile_id=? ORDER BY identity_type,created_at",
                    (canonical_id,),
                ).fetchall()
            ]

        signals.sort(key=lambda item: str(item.get("observed_at") or ""), reverse=True)
        return {
            "mock": True,
            "requested_profile_id": profile_id,
            "canonical_profile_id": canonical_id,
            "requested_profile": dict(requested),
            "lineage_profiles": lineage,
            "identities": identities,
            "active_signals": [item for item in signals if item["status"] == "active"],
            "signal_history": signals,
            "latest_booking_context": self.latest_booking_context(canonical_id),
        }

    def mock_debug_summary(self, profile_id: str) -> dict[str, Any]:
        """Return a compact profile view grouped by evidence source and certainty."""
        full = self.mock_debug_view(profile_id)

        def compact(signal: dict[str, Any]) -> dict[str, Any]:
            return {
                "category": signal["category"],
                "key": signal["key"],
                "value": signal["value"],
                "description": signal.get("description"),
                "confidence": signal.get("confidence"),
                "observed_at": signal.get("observed_at"),
                "source_ref": signal.get("source_ref"),
            }

        levels: dict[str, dict[str, list[dict[str, Any]]]] = {
            source: {certainty: [] for certainty in ("known", "likely", "possible")}
            for source in ("explicit_user", "implicit_user", "trusted_domain")
        }
        categories: dict[str, list[dict[str, Any]]] = {}
        for signal in full["active_signals"]:
            source = str(signal.get("source_type") or "implicit_user")
            certainty = str(signal.get("certainty") or "possible")
            levels.setdefault(source, {}).setdefault(certainty, []).append(compact(signal))
            categories.setdefault(str(signal["category"]), []).append(compact(signal))

        history = full["signal_history"]
        identity_counts: dict[str, int] = {}
        for identity in full["identities"]:
            identity_type = str(identity["identity_type"])
            identity_counts[identity_type] = identity_counts.get(identity_type, 0) + 1

        return {
            "mock": True,
            "view": "summary",
            "requested_profile_id": full["requested_profile_id"],
            "canonical_profile_id": full["canonical_profile_id"],
            "profile": full["requested_profile"],
            "merged_profile_ids": [
                item["id"]
                for item in full["lineage_profiles"]
                if item["id"] != full["canonical_profile_id"]
            ],
            "identity_counts": identity_counts,
            "signal_counts": {
                "active": len(full["active_signals"]),
                "superseded": sum(item["status"] == "superseded" for item in history),
                "retracted": sum(item["status"] == "retracted" for item in history),
                "total_history": len(history),
            },
            "levels": levels,
            "categories": categories,
            "recent_changes": [
                {
                    **compact(item),
                    "status": item["status"],
                    "source_type": item["source_type"],
                    "certainty": item["certainty"],
                    "superseded_by_signal_id": item.get("superseded_by_signal_id"),
                }
                for item in history
                if item["status"] != "active"
            ][:20],
            "latest_booking_context": full["latest_booking_context"],
            "full_view_url": f"/api/v1/mock/user-profiles/{full['requested_profile_id']}",
        }
