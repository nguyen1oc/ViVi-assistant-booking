from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
from datetime import UTC, timedelta

from src.database.redis_client import redis_client
from src.database.rows import DbRow
from src.security.rate_limit import consume_rate_limit_counter
from src.services.booking.base import BookingBase
from src.services.booking.common import (
    is_valid_customer_email,
    is_valid_customer_phone,
    iso,
    new_id,
    normalize_phone,
    parse_utc,
)
from src.services.booking.errors import BookingError

_id = new_id
logger = logging.getLogger(__name__)

# Quyền cấp cho phiên truy cập, theo mục đích người dùng khai lúc xin OTP.
#
# ĐỂ Ở ĐÂY, ĐỪNG CHÉP LẠI. Trước 18/08/2026 bảng này tồn tại HAI bản giống hệt — một trong
# request_access, một trong verify_access. Thêm purpose "manage" vào bản đầu mà quên bản sau
# khiến xin OTP thì được nhưng nhập mã lại nổ KeyError: 'manage' → HTTP 500, và giao diện chỉ
# hiện câu chung chung "Yêu cầu không thành công." vì thân lỗi 500 không có message.
ACCESS_PERMISSIONS: dict[str, list[str]] = {
    "lookup": ["read_booking"],
    "reschedule": ["read_booking", "search_reschedule", "hold_reschedule", "confirm_reschedule", "update_details"],
    "cancel": ["read_booking", "cancel_booking"],
    "update_details": ["read_booking", "update_details"],
    "update_notifications": ["read_booking", "update_notifications"],
    # Một phiên quản lý đầy đủ: xem, đổi giờ và huỷ trong CÙNG một lần xác thực OTP, để màn
    # tra cứu hiện được nút "Huỷ lịch" mà không bắt người dùng xác thực lại lần nữa.
    "manage": [
        "read_booking",
        "search_reschedule",
        "hold_reschedule",
        "confirm_reschedule",
        "update_details",
        "cancel_booking",
    ],
    # Xác thực OTP khi tạo mới / chốt lịch đặt lái thử
    "confirm_booking": [
        "read_booking",
        "confirm_booking",
        "update_details",
    ],
}


class AccessService(BookingBase):
    def _check_rate_counter(self, *, bucket_key: str, limit: int, window_seconds: int) -> None:
        now_dt = self.now()
        if now_dt.tzinfo is None:
            now_dt = now_dt.replace(tzinfo=UTC)
        with self.db.transaction(immediate=True) as c:
            decision = consume_rate_limit_counter(
                c,
                bucket_key=bucket_key,
                limit=limit,
                window_seconds=window_seconds,
                now=now_dt,
            )
            if not decision.allowed:
                raise BookingError(
                    "RATE_LIMIT_EXCEEDED",
                    f"Vui lòng thử lại sau {decision.retry_after_seconds} giây.",
                    retryable=True,
                )

    def request_access(
        self,
        booking_code: str | None,
        contact_value: str,
        purpose: str,
        preferred_channel: str = "sms",
        *,
        expose_otp: bool = False,
    ) -> dict:
        permissions = ACCESS_PERMISSIONS
        # Keep compatibility with the original positional API:
        # request_access(booking_code, contact_value, purpose). New callers use
        # explicit keywords in the order contact_value, purpose, booking_code.
        if booking_code in permissions and purpose not in permissions:
            contact_value, purpose, booking_code = purpose, booking_code, contact_value
        if purpose not in permissions:
            raise BookingError("INVALID_INPUT", "Mục đích không hợp lệ.")
        eligible_statuses = (
            ("confirmed", "checked_in", "completed", "no_show")
            if purpose == "lookup"
            else ("held",) if purpose == "confirm_booking"
            else ("confirmed",)
        )
        status_placeholders = ",".join("?" for _ in eligible_statuses)
        normalized_code = (booking_code or "").strip().upper()
        if preferred_channel not in {"zalo", "sms", "email"}:
            raise BookingError("INVALID_INPUT", "Kênh OTP phải là zalo, sms hoặc email.")
        contact = contact_value.strip()
        normalized = contact.lower() if preferred_channel == "email" else normalize_phone(contact)
        if not normalized or (preferred_channel == "email") != ("@" in normalized):
            raise BookingError("INVALID_INPUT", "Thông tin liên hệ không phù hợp với kênh OTP.")
        if preferred_channel == "email" and not is_valid_customer_email(contact):
            raise BookingError("INVALID_INPUT", "Email phải đúng định dạng, tối đa 30 ký tự trước @ và 20 ký tự sau @.")
        if preferred_channel != "email" and not is_valid_customer_phone(contact):
            raise BookingError("INVALID_INPUT", "Số điện thoại phải gồm đúng 10 chữ số và bắt đầu bằng 0.")
        destination_hash = self._hash(normalized, "destination")
        self._check_rate_counter(
            bucket_key=f"otp_request:contact:{destination_hash}",
            limit=self.otp_request_per_contact_per_hour,
            window_seconds=3600,
        )
        with self.db.transaction(immediate=True) as c:
            if normalized_code:
                booking = c.execute(
                    f"SELECT * FROM bookings WHERE (booking_code=? OR lower(id)=lower(?)) AND status IN ({status_placeholders})",
                    (normalized_code, normalized_code, *eligible_statuses),
                ).fetchone()
            elif preferred_channel == "email":
                booking = c.execute(
                    "SELECT b.* FROM bookings b JOIN people booker ON booker.id=b.booker_person_id "
                    "LEFT JOIN people driver ON driver.id=b.driver_person_id "
                    f"WHERE (lower(booker.email)=? OR lower(driver.email)=?) AND b.status IN ({status_placeholders}) "
                    "ORDER BY COALESCE(b.confirmed_at,b.updated_at,b.held_at) DESC LIMIT 1",
                    (normalized, normalized, *eligible_statuses),
                ).fetchone()
            else:
                booking = c.execute(
                    "SELECT b.* FROM bookings b JOIN people booker ON booker.id=b.booker_person_id "
                    "LEFT JOIN people driver ON driver.id=b.driver_person_id "
                    f"WHERE (booker.normalized_phone=? OR driver.normalized_phone=?) AND b.status IN ({status_placeholders}) "
                    "ORDER BY COALESCE(b.confirmed_at,b.updated_at,b.held_at) DESC LIMIT 1",
                    (normalized, normalized, *eligible_statuses),
                ).fetchone()
            if not booking:
                raise BookingError("BOOKING_ACCESS_NOT_AVAILABLE", "Không tìm thấy lịch hẹn thuộc email này.")
            if purpose != "confirm_booking" or (booking["booker_person_id"] or booking["driver_person_id"]):
                contact_matches = c.execute(
                    "SELECT 1 FROM people WHERE id IN (?,?) AND (lower(email)=? OR normalized_phone=? OR phone=?) LIMIT 1",
                    (booking["booker_person_id"], booking["driver_person_id"], normalized, normalized, contact),
                ).fetchone()
                if not contact_matches and purpose != "confirm_booking":
                    raise BookingError("BOOKING_ACCESS_NOT_AVAILABLE", "Email không thuộc lịch hẹn này.")
            if preferred_channel == "zalo" and not hasattr(self.otp_sender, "is_linked"):
                raise BookingError("ZALO_NOT_CONFIGURED", "Kênh Zalo chưa được cấu hình.")
            if preferred_channel == "zalo" and not self.otp_sender.is_linked(contact_value):
                raise BookingError("ZALO_NOT_LINKED", "Số điện thoại chưa liên kết với Zalo Bot.")
            if booking["status"] not in eligible_statuses:
                raise BookingError("BOOKING_ACCESS_NOT_AVAILABLE", "Không thể cấp quyền truy cập booking.")
            latest = c.execute(
                "SELECT created_at FROM otp_challenges WHERE booking_id=? AND destination_hash=? "
                "AND status='pending' "
                "ORDER BY created_at DESC LIMIT 1",
                (booking["id"], destination_hash),
            ).fetchone()
            if latest:
                elapsed = (parse_utc(self.now()) - parse_utc(latest["created_at"])).total_seconds()
                if elapsed < self.otp_resend_cooldown_seconds:
                    remaining = max(1, int(self.otp_resend_cooldown_seconds - elapsed))
                    raise BookingError("OTP_RATE_LIMITED", f"Vui lòng chờ {remaining} giây trước khi gửi lại OTP.", retryable=True)
            c.execute(
                "UPDATE otp_challenges SET status='superseded' WHERE booking_id=? AND status='pending'",
                (booking["id"],),
            )
            code = f"{secrets.randbelow(1_000_000):06d}"
            salt = secrets.token_hex(8)
            challenge_id = _id("otp")
            redis_client.set_otp(challenge_id, code, ttl_seconds=int(self.otp_ttl_seconds))
            expires_at = self.now() + timedelta(seconds=self.otp_ttl_seconds)
            masked = self._mask(contact_value)
            c.execute(
                "INSERT INTO otp_challenges(id,booking_id,purpose,channel,destination_masked,"
                "destination_hash,code_hash,expires_at,max_attempts,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    challenge_id,
                    booking["id"],
                    purpose,
                    preferred_channel,
                    masked,
                    destination_hash,
                    salt + ":" + self._hash(code, salt),
                    iso(expires_at),
                    self.otp_max_attempts,
                    iso(self.now()),
                ),
            )
            self._event(c, booking["id"], "otp_requested", "user", {"purpose": purpose})
        try:
            delivery = self.otp_sender.send(
                channel=preferred_channel,
                destination=contact_value,
                code=code,
                expires_in_seconds=self.otp_ttl_seconds,
            )
        except ValueError as err:
            self._invalidate_failed_delivery(challenge_id, booking["id"], preferred_channel, "channel_unavailable")
            raise BookingError("OTP_CHANNEL_UNAVAILABLE", "Kênh OTP được chọn tạm thời chưa được cấu hình.") from err
        except Exception:
            logger.exception(
                "otp.delivery_exception challenge_id=%s channel=%s",
                challenge_id,
                preferred_channel,
            )
            self._invalidate_failed_delivery(challenge_id, booking["id"], preferred_channel, "provider_exception")
            raise BookingError(
                "OTP_DELIVERY_FAILED",
                "Không thể gửi mã OTP. Vui lòng thử lại sau.",
                retryable=True,
            )

        delivered = bool(delivery) and (
            getattr(delivery, "provider_status", None) in {"sent", "mocked"}
            or bool(getattr(delivery, "is_mock", False))
        )
        if not delivered:
            provider = getattr(delivery, "provider", "unknown")
            provider_status = getattr(delivery, "provider_status", "unknown")
            retryable = bool(getattr(delivery, "retryable", True))
            logger.warning(
                "otp.delivery_failed challenge_id=%s channel=%s provider=%s provider_status=%s retryable=%s provider_response=%s",
                challenge_id,
                preferred_channel,
                provider,
                provider_status,
                retryable,
                getattr(delivery, "sanitized_response", {}),
            )
            self._invalidate_failed_delivery(challenge_id, booking["id"], preferred_channel, provider_status)
            raise BookingError(
                "OTP_DELIVERY_FAILED",
                "Không thể gửi mã OTP. Vui lòng thử lại sau.",
                retryable=retryable,
            )
        result = {
            "challenge_id": challenge_id,
            "destination_masked": masked,
            "expires_at": iso(expires_at),
            "retry_after_seconds": self.otp_resend_cooldown_seconds,
            "max_attempts": self.otp_max_attempts,
            "available_channels": [preferred_channel],
            "provider_status": getattr(delivery, "provider_status", "mocked"),
            "provider_message_id": getattr(delivery, "provider_message_id", None),
            "is_mock": getattr(delivery, "is_mock", True),
            "missing_fields": [],
            "suggested_next_action": "enter_otp",
        }
        if expose_otp and result["is_mock"]:
            result["otp_code"] = code
        return result

    def _invalidate_failed_delivery(
        self, challenge_id: str, booking_id: str, channel: str, provider_status: str
    ) -> None:
        """OTP that was not delivered must never be usable for authentication."""
        with self.db.transaction(immediate=True) as c:
            c.execute("UPDATE otp_challenges SET status='superseded' WHERE id=? AND status='pending'", (challenge_id,))
            self._event(
                c,
                booking_id,
                "otp_delivery_failed",
                "system",
                {"challenge_id": challenge_id, "channel": channel, "provider_status": provider_status},
            )

    def _hash(self, value, salt):
        return hmac.new(self.otp_secret, (salt + value).encode(), hashlib.sha256).hexdigest()

    @staticmethod
    def _mask(value):
        if "@" in value:
            account, domain = value.split("@", 1)
            return account[:1] + "***@" + domain
        return "*" * max(0, len(value) - 3) + value[-3:]

    def verify_access(self, challenge_id: str, otp_code: str) -> dict:
        with self.db.connect() as c:
            challenge_exists = c.execute("SELECT id FROM otp_challenges WHERE id=?", (challenge_id,)).fetchone()
        if not challenge_exists:
            raise BookingError("OTP_INVALID", "OTP không hợp lệ.")
        self._check_rate_counter(
            bucket_key=f"otp_verify:challenge:{challenge_id}",
            limit=self.otp_verify_per_challenge_per_minute,
            window_seconds=60,
        )
        with self.db.transaction(immediate=True) as c:
            ch = c.execute("SELECT * FROM otp_challenges WHERE id=?", (challenge_id,)).fetchone()
            if not ch:
                raise BookingError("OTP_INVALID", "OTP không hợp lệ.")
            if ch["status"] != "pending":
                raise BookingError(
                    "OTP_LOCKED" if ch["status"] == "locked" else "OTP_INVALID", "OTP không còn dùng được."
                )
            if parse_utc(ch["expires_at"]) <= parse_utc(self.now()):
                c.execute("UPDATE otp_challenges SET status='expired' WHERE id=?", (challenge_id,))
                raise BookingError("OTP_EXPIRED", "OTP đã hết hạn.")
            salt, digest = ch["code_hash"].split(":", 1)
            if not hmac.compare_digest(self._hash(otp_code, salt), digest):
                attempts = ch["attempt_count"] + 1
                status = "locked" if attempts >= ch["max_attempts"] else "pending"
                c.execute(
                    "UPDATE otp_challenges SET attempt_count=?,status=? WHERE id=?", (attempts, status, challenge_id)
                )
                # Persist the security counter before raising the domain error;
                # otherwise the transaction context would roll it back.
                c.commit()
                error = BookingError(
                    "OTP_LOCKED" if status == "locked" else "OTP_INVALID",
                    f"OTP không đúng. Còn {max(0, ch['max_attempts'] - attempts)} lần thử.",
                )
                error.remaining_attempts = max(0, ch["max_attempts"] - attempts)
                raise error
            now = iso(self.now())
            c.execute(
                "UPDATE otp_challenges SET status='verified',verified_at=?,consumed_at=? WHERE id=?",
                (now, now, challenge_id),
            )
            raw = secrets.token_urlsafe(32)
            token_hash = self._hash(raw, "session")
            # Purpose lạ (dữ liệu cũ, hoặc thêm purpose mới mà quên khai) thì hạ về quyền đọc
            # thay vì ném KeyError thành lỗi 500 — người dùng đã nhập đúng mã, không có lý do
            # gì để họ nhận một lỗi hệ thống không đọc được.
            perms = ACCESS_PERMISSIONS.get(ch["purpose"], ACCESS_PERMISSIONS["lookup"])
            expiry = self.now() + timedelta(seconds=self.access_session_ttl_seconds)
            c.execute(
                "INSERT INTO booking_access_sessions VALUES(?,?,?,?,?,?,?,?)",
                (_id("session"), token_hash, ch["booking_id"], challenge_id, json.dumps(perms), iso(expiry), None, now),
            )
            self._event(c, ch["booking_id"], "otp_verified", "user")
            return {
                "access_session_token": raw,
                "booking_id": ch["booking_id"],
                "permissions": perms,
                "session_expires_at": iso(expiry),
            }

    def verified_identity(self, challenge_id: str) -> dict | None:
        """Resolve the person/contact actually verified by a consumed OTP challenge."""
        with self.db.connect() as c:
            challenge = c.execute("SELECT booking_id,destination_hash,status FROM otp_challenges WHERE id=?", (challenge_id,)).fetchone()
            if not challenge or challenge["status"] != "verified":
                return None
            booking = c.execute("SELECT booker_person_id,driver_person_id FROM bookings WHERE id=?", (challenge["booking_id"],)).fetchone()
            if not booking:
                return None
            for person_id in dict.fromkeys((booking["booker_person_id"], booking["driver_person_id"])):
                if not person_id:
                    continue
                person = c.execute("SELECT id,normalized_email,normalized_phone,email,phone FROM people WHERE id=?", (person_id,)).fetchone()
                for value in (person["normalized_email"], person["email"], person["normalized_phone"], person["phone"]):
                    if value and hmac.compare_digest(self._hash(str(value).casefold() if "@" in str(value) else str(value), "destination"), challenge["destination_hash"]):
                        return dict(person)
        return None

    def get_booking_details(
        self, access_session_token: str, *, booking_id: str | None = None, booking_code: str | None = None
    ) -> dict:
        if (booking_id is None) == (booking_code is None):
            raise BookingError("INVALID_INPUT", "Cần đúng một trong booking_id hoặc booking_code.")
        with self.db.connect() as c:
            session = c.execute(
                "SELECT * FROM booking_access_sessions WHERE token_hash=?",
                (self._hash(access_session_token, "session"),),
            ).fetchone()
            if not session or session["revoked_at"] or parse_utc(session["expires_at"]) <= parse_utc(self.now()):
                raise BookingError("ACCESS_SESSION_EXPIRED", "Phiên truy cập đã hết hạn.")
            if "read_booking" not in json.loads(session["permissions_json"]):
                raise BookingError("ACCESS_DENIED", "Không có quyền đọc booking.")
            target_id = booking_id or c.execute("SELECT id FROM bookings WHERE booking_code=?", (booking_code,)).fetchone()
            target_id = target_id["id"] if target_id and not isinstance(target_id, str) else target_id
            anchor = c.execute("SELECT * FROM bookings WHERE id=?", (session["booking_id"],)).fetchone()
            if not target_id or not self._same_contact_owner(c, anchor, target_id):
                raise BookingError("ACCESS_SESSION_SCOPE_MISMATCH", "Phiên không thuộc booking này.")
            target_booking = c.execute("SELECT * FROM bookings WHERE id=?", (target_id,)).fetchone()
            result = self._draft(c, target_id, require_held=False)
            result["slot"] = self._row(
                c.execute("SELECT * FROM test_drive_slots WHERE id=?", (result["slot_id"],)).fetchone()
            )
            catalog = c.execute(
                "SELECT m.*,v.id variant_id,v.name variant_name,s.name showroom_name,s.address showroom_address FROM test_drive_slots t JOIN demo_vehicles d ON d.id=t.demo_vehicle_id JOIN vehicle_variants v ON v.id=d.variant_id JOIN vehicle_models m ON m.id=v.model_id JOIN showrooms s ON s.id=t.showroom_id WHERE t.id=?",
                (result["slot_id"],),
            ).fetchone()
            result["vehicle"] = self._row(catalog)
            result["showroom"] = {"id": result["slot"]["showroom_id"], "name": catalog["showroom_name"], "address": catalog["showroom_address"]}
            advisor = c.execute("SELECT full_name,phone FROM sales_staff WHERE id=?", (target_booking["assigned_sales_staff_id"],)).fetchone() if target_booking["assigned_sales_staff_id"] else None
            result["advisor"] = self._row(advisor) or {"full_name": "Chưa phân công", "phone": None}
            permissions = json.loads(session["permissions_json"])
            result["allowed_actions"] = [
                action
                for action in ("reschedule", "cancel", "update_details", "update_notifications")
                if result["status"] == "confirmed"
                and {
                    "reschedule": "confirm_reschedule",
                    "cancel": "cancel_booking",
                    "update_details": "update_details",
                    "update_notifications": "update_notifications",
                }[action]
                in permissions
            ]
            result["session_expires_at"] = session["expires_at"]
            return result

    def list_bookings(self, access_session_token: str) -> list[dict]:
        with self.db.connect() as c:
            session = c.execute("SELECT * FROM booking_access_sessions WHERE token_hash=?", (self._hash(access_session_token, "session"),)).fetchone()
            if not session or session["revoked_at"] or parse_utc(session["expires_at"]) <= parse_utc(self.now()):
                raise BookingError("ACCESS_SESSION_EXPIRED", "Phiên truy cập đã hết hạn.")
            anchor = c.execute("SELECT * FROM bookings WHERE id=?", (session["booking_id"],)).fetchone()
            emails, phones = self._owner_contacts(c, anchor)
            owner_clauses: list[str] = []
            owner_params: list[str] = []
            if emails:
                marks = ",".join("?" * len(emails))
                owner_clauses.append(
                    f"(booker.normalized_email IN ({marks}) OR driver.normalized_email IN ({marks}))"
                )
                ordered_emails = sorted(emails)
                owner_params.extend((*ordered_emails, *ordered_emails))
            if phones:
                marks = ",".join("?" * len(phones))
                owner_clauses.append(
                    f"(booker.normalized_phone IN ({marks}) OR driver.normalized_phone IN ({marks}))"
                )
                ordered_phones = sorted(phones)
                owner_params.extend((*ordered_phones, *ordered_phones))
            if not owner_clauses:
                return []
            owner_filter = " OR ".join(owner_clauses)
            rows = c.execute(
                f"SELECT b.id,b.booking_code,b.status,b.confirmed_at,m.name vehicle_name,s.name showroom_name,t.start_at "
                f"FROM bookings b JOIN people booker ON booker.id=b.booker_person_id JOIN test_drive_slots t ON t.id=b.slot_id JOIN demo_vehicles d ON d.id=t.demo_vehicle_id JOIN vehicle_variants v ON v.id=d.variant_id JOIN vehicle_models m ON m.id=v.model_id JOIN showrooms s ON s.id=t.showroom_id "
                f"LEFT JOIN people driver ON driver.id=b.driver_person_id WHERE b.booking_code IS NOT NULL AND b.status IN ('confirmed','checked_in','completed','no_show') AND ({owner_filter}) ORDER BY CASE WHEN t.start_at >= ? THEN 0 ELSE 1 END, CASE WHEN t.start_at >= ? THEN t.start_at END ASC, t.start_at DESC",
                (*owner_params, iso(self.now()), iso(self.now())),
            ).fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def _owner_contacts(c, booking) -> tuple[set[str], set[str]]:
        if not booking:
            return set(), set()
        person_ids = [booking["booker_person_id"], booking["driver_person_id"]]
        rows = c.execute(
            "SELECT normalized_email,normalized_phone FROM people WHERE id IN (?,?)",
            person_ids,
        ).fetchall()
        emails = {(row["normalized_email"] or "").lower() for row in rows if row["normalized_email"]}
        phones = {row["normalized_phone"] for row in rows if row["normalized_phone"]}
        return emails, phones

    def _same_contact_owner(self, c, anchor, target_id: str) -> bool:
        target = c.execute("SELECT * FROM bookings WHERE id=?", (target_id,)).fetchone()
        if not target:
            return False
        anchor_emails, anchor_phones = self._owner_contacts(c, anchor)
        target_emails, target_phones = self._owner_contacts(c, target)
        return bool((anchor_emails & target_emails) or (anchor_phones & target_phones))

    def _require_access(self, c, token: str, booking_id: str, permission: str) -> DbRow:
        session = c.execute(
            "SELECT * FROM booking_access_sessions WHERE token_hash=?", (self._hash(token, "session"),)
        ).fetchone()
        if not session or session["revoked_at"] or parse_utc(session["expires_at"]) <= parse_utc(self.now()):
            raise BookingError("ACCESS_SESSION_EXPIRED", "Phiên truy cập đã hết hạn.")
        anchor = c.execute("SELECT * FROM bookings WHERE id=?", (session["booking_id"],)).fetchone()
        if not self._same_contact_owner(c, anchor, booking_id):
            raise BookingError("ACCESS_SESSION_SCOPE_MISMATCH", "Phiên không thuộc booking này.")
        if permission not in json.loads(session["permissions_json"]):
            raise BookingError("ACCESS_DENIED", "Phiên không có quyền thực hiện thao tác này.")
        return session
