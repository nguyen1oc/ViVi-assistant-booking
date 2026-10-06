from __future__ import annotations

import hashlib
import json
from typing import Any

from src.services.booking.common import iso, new_id, parse_utc, row_to_dict
from src.services.booking.errors import BookingError

_id = new_id


class BookingBase:
    IDEMPOTENCY_PREFIXES = {
        "hold_slot": "hold:",
        "confirm_booking": "confirm:",
        "hold_reschedule": "reschedule-hold:",
        "confirm_reschedule": "reschedule-confirm:",
        "cancel_booking": "cancel:",
        "record_license_check": "staff-license:",
        "check_in_booking": "staff-checkin:",
        "test_drive_completed": "staff-complete:",
        "booking_marked_no_show": "staff-noshow:",
    }

    def __getattr__(self, name: str) -> Any:
        """Support attributes and helpers supplied by sibling booking mixins.

        The concrete BookingService composes this base with the operational
        service mixins and assigns shared dependencies in its initializer.
        """
        raise AttributeError(name)

    @staticmethod
    def _row(row):
        return row_to_dict(row)

    def _event(self, c, booking_id: str, event: str, actor: str = "system", payload: dict | None = None):
        blocked = {
            "otp",
            "otp_code",
            "access_token",
            "access_session_token",
            "phone",
            "email",
            "contact_value",
            "reason",
            "note",
        }
        safe_payload = {key: value for key, value in (payload or {}).items() if key.lower() not in blocked}
        actor_id = safe_payload.get("staff_id") if actor == "staff" else None
        c.execute(
            "INSERT INTO booking_events VALUES(?,?,?,?,?,?,?)",
            (_id("evt"), booking_id, event, actor, actor_id, json.dumps(safe_payload), iso(self.now())),
        )

    @staticmethod
    def _request_hash(payload: dict) -> str:
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @classmethod
    def _idempotent_response(cls, c, action_id: str, operation: str, payload: dict):
        prefix = cls.IDEMPOTENCY_PREFIXES[operation]
        if not action_id.startswith(prefix) or len(action_id) <= len(prefix):
            raise BookingError("INVALID_INPUT", f"ui_action_id của {operation} phải bắt đầu bằng '{prefix}'.")
        request_hash = cls._request_hash(payload)
        row = c.execute(
            "SELECT operation,request_hash,response_json FROM idempotency_records WHERE action_id=?", (action_id,)
        ).fetchone()
        if not row:
            return None
        if row["operation"] != operation:
            raise BookingError("IDEMPOTENCY_CONFLICT", "Idempotency key đã được dùng cho thao tác khác.")
        if row["request_hash"] and row["request_hash"] != request_hash:
            raise BookingError("IDEMPOTENCY_CONFLICT", "Idempotency key đã được dùng với payload khác.")
        return json.loads(row["response_json"])

    @classmethod
    def _save_idempotency(cls, c, action_id: str, operation: str, payload: dict, response: dict, created_at: str):
        c.execute(
            "INSERT INTO idempotency_records(action_id,operation,request_hash,status,response_json,created_at) "
            "VALUES(?,?,?,'succeeded',?,?)",
            (action_id, operation, cls._request_hash(payload), json.dumps(response), created_at),
        )

    @staticmethod
    def _overlaps(start_a: str, end_a: str, start_b: str, end_b: str) -> bool:
        return parse_utc(start_a) < parse_utc(end_b) and parse_utc(end_a) > parse_utc(start_b)

    def _available_sales_staff(
        self,
        c,
        *,
        showroom_id: str,
        start_at: str,
        end_at: str,
        slot_id: str | None = None,
        lock: bool = False,
    ) -> tuple[list[dict[str, Any]], bool]:
        """Return staff who can own this appointment and whether capacity is tracked.

        An installation without any active staff at a showroom keeps the legacy
        untracked behavior. Once staff data exists, every held/booked overlap
        consumes one distinct consultant.
        """
        query = (
            "SELECT id,full_name,phone FROM sales_staff "
            "WHERE showroom_id=? AND status='active' AND is_active=1 ORDER BY id"
        )
        if lock and c.dialect == "postgres":
            query += " FOR UPDATE"
        staff_rows = [dict(row) for row in c.execute(query, (showroom_id,)).fetchall()]
        if not staff_rows:
            return [], False

        preferred_ids: set[str] = set()
        if slot_id:
            preferred_ids = {
                str(row["sales_staff_id"])
                for row in c.execute(
                    "SELECT sales_staff_id FROM slot_sales_assignments "
                    "WHERE slot_id=? AND assignment_role='test_drive_consultant' AND status='assigned'",
                    (slot_id,),
                ).fetchall()
            }

        now = parse_utc(self.now())
        candidates: list[dict[str, Any]] = []
        for staff in staff_rows:
            staff_id = str(staff["id"])
            unavailable = any(
                self._overlaps(row["start_at"], row["end_at"], start_at, end_at)
                for row in c.execute(
                    "SELECT start_at,end_at FROM staff_unavailability WHERE sales_staff_id=?",
                    (staff_id,),
                ).fetchall()
            )
            if unavailable:
                continue
            occupied = False
            for row in c.execute(
                "SELECT s.id,s.start_at,s.end_at,s.status,s.held_until "
                "FROM slot_sales_assignments a JOIN test_drive_slots s ON s.id=a.slot_id "
                "WHERE a.sales_staff_id=? AND a.assignment_role='test_drive_consultant' "
                "AND a.status='assigned' AND s.id<>? AND s.status IN ('held','booked')",
                (staff_id, slot_id or ""),
            ).fetchall():
                active = row["status"] == "booked" or (
                    row["status"] == "held"
                    and (row["held_until"] is None or parse_utc(row["held_until"]) > now)
                )
                if active and self._overlaps(row["start_at"], row["end_at"], start_at, end_at):
                    occupied = True
                    break
            if not occupied:
                candidates.append(staff)

        candidates.sort(key=lambda staff: (str(staff["id"]) not in preferred_ids, str(staff["id"])))
        return candidates, True

    def _assign_sales_staff_to_slot(self, c, *, slot_id: str, staff_id: str, now: str) -> None:
        role = "test_drive_consultant"
        c.execute(
            "UPDATE slot_sales_assignments SET status='reassigned',updated_at=? "
            "WHERE slot_id=? AND assignment_role=? AND status='assigned' AND sales_staff_id<>?",
            (now, slot_id, role, staff_id),
        )
        existing = c.execute(
            "SELECT id FROM slot_sales_assignments "
            "WHERE slot_id=? AND sales_staff_id=? AND assignment_role=?",
            (slot_id, staff_id, role),
        ).fetchone()
        if existing:
            c.execute(
                "UPDATE slot_sales_assignments SET status='assigned',updated_at=? WHERE id=?",
                (now, existing["id"]),
            )
        else:
            c.execute(
                "INSERT INTO slot_sales_assignments("
                "id,slot_id,sales_staff_id,assignment_role,status,created_at,updated_at"
                ") VALUES(?,?,?,?,?,?,?)",
                (_id("assign"), slot_id, staff_id, role, "assigned", now, now),
            )
