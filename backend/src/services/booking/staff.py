from __future__ import annotations

from datetime import timedelta

from src.services.booking.base import BookingBase
from src.services.booking.common import iso, parse_utc
from src.services.booking.errors import BookingError


class StaffOperationService(BookingBase):
    def _staff_booking(self, c, booking_id: str, staff_id: str):
        row = c.execute(
            "SELECT b.*,t.showroom_id,t.start_at FROM bookings b "
            "JOIN test_drive_slots t ON t.id=b.slot_id "
            "JOIN sales_staff s ON s.id=? AND s.showroom_id=t.showroom_id "
            "WHERE b.id=? AND s.status='active' AND s.is_active=1 "
            "AND EXISTS (SELECT 1 FROM slot_sales_assignments ssa WHERE ssa.slot_id=t.id "
            "AND ssa.sales_staff_id=s.id AND ssa.assignment_role='test_drive_consultant' "
            "AND ssa.status='assigned')",
            (staff_id, booking_id),
        ).fetchone()
        if not row:
            raise BookingError("ACCESS_DENIED", "Nhân viên không có quyền với booking này.")
        return row

    def record_license_check(
        self,
        booking_id: str,
        staff_id: str,
        ui_action_id: str,
        *,
        original_document_presented: bool,
        license_class_matches: bool,
        is_currently_valid: bool,
        result: str,
        rejection_reason: str | None = None,
    ) -> dict:
        if result not in {"verified", "rejected"}:
            raise BookingError("INVALID_INPUT", "Kết quả kiểm tra GPLX không hợp lệ.")
        verified = all((original_document_presented, license_class_matches, is_currently_valid))
        if result == "verified" and not verified:
            raise BookingError("INVALID_INPUT", "Không thể xác minh GPLX khi điều kiện kiểm tra chưa đạt.")
        request_payload = {
            "booking_id": booking_id,
            "staff_id": staff_id,
            "original_document_presented": original_document_presented,
            "license_class_matches": license_class_matches,
            "is_currently_valid": is_currently_valid,
            "result": result,
            "rejection_reason": rejection_reason,
        }
        with self.db.transaction(immediate=True) as c:
            booking = self._staff_booking(c, booking_id, staff_id)
            cached = self._idempotent_response(c, ui_action_id, "record_license_check", request_payload)
            if cached:
                return cached
            if booking["status"] != "confirmed":
                raise BookingError("INVALID_STATE_TRANSITION", "Booking phải ở trạng thái confirmed.")
            now = iso(self.now())
            c.execute(
                "UPDATE booking_driver_details SET license_check_status=?,checked_at=?,checked_by=?,rejection_reason=?,updated_at=? WHERE booking_id=?",
                (result, now, staff_id, rejection_reason if result == "rejected" else None, now, booking_id),
            )
            self._event(
                c,
                booking_id,
                "license_verified" if result == "verified" else "license_rejected",
                "staff",
                {"staff_id": staff_id},
            )
            response = {
                "license_check_status": result,
                "checked_at": now,
                "checked_by": staff_id,
                "eligible_for_check_in": result == "verified",
            }
            self._save_idempotency(c, ui_action_id, "record_license_check", request_payload, response, now)
            return response

    def check_in_booking(self, booking_id: str, staff_id: str, ui_action_id: str) -> dict:
        request_payload = {"booking_id": booking_id, "staff_id": staff_id}
        with self.db.transaction(immediate=True) as c:
            booking = self._staff_booking(c, booking_id, staff_id)
            cached = self._idempotent_response(c, ui_action_id, "check_in_booking", request_payload)
            if cached:
                return cached
            detail = c.execute(
                "SELECT license_check_status FROM booking_driver_details WHERE booking_id=?", (booking_id,)
            ).fetchone()
            if booking["status"] != "confirmed":
                raise BookingError("INVALID_STATE_TRANSITION", "Booking không ở trạng thái confirmed.")
            if not detail or detail["license_check_status"] != "verified":
                raise BookingError("LICENSE_NOT_VERIFIED", "GPLX chưa được nhân viên xác minh.")
            start = self._parse_time(booking["start_at"])
            if not start - timedelta(minutes=60) <= self.now() <= start + timedelta(minutes=30):
                raise BookingError("INVALID_STATE_TRANSITION", "Booking nằm ngoài cửa sổ check-in.")
            now = iso(self.now())
            c.execute(
                "UPDATE bookings SET status='checked_in',checked_in_at=?,version=version+1,updated_at=? WHERE id=?",
                (now, now, booking_id),
            )
            self._event(c, booking_id, "driver_checked_in", "staff", {"staff_id": staff_id})
            response = {"booking_id": booking_id, "status": "checked_in", "checked_in_at": now}
            self._save_idempotency(c, ui_action_id, "check_in_booking", request_payload, response, now)
            return response

    def complete_test_drive(
        self, booking_id: str, staff_id: str, ui_action_id: str, completion_note: str | None = None
    ) -> dict:
        return self._staff_transition(
            booking_id,
            staff_id,
            ui_action_id,
            "checked_in",
            "completed",
            "test_drive_completed",
            "completed_at",
            completion_note,
        )

    def mark_no_show(self, booking_id: str, staff_id: str, ui_action_id: str, reason: str | None = None) -> dict:
        with self.db.connect() as c:
            booking = self._staff_booking(c, booking_id, staff_id)
            if self.now() <= self._parse_time(booking["start_at"]) + timedelta(minutes=30):
                raise BookingError("INVALID_STATE_TRANSITION", "Chưa qua grace period để đánh dấu no-show.")
        return self._staff_transition(
            booking_id, staff_id, ui_action_id, "confirmed", "no_show", "booking_marked_no_show", None, reason
        )

    def _staff_transition(self, booking_id, staff_id, action_id, expected, target, event, timestamp_column, note):
        request_payload = {"booking_id": booking_id, "staff_id": staff_id, "note": note}
        with self.db.transaction(immediate=True) as c:
            booking = self._staff_booking(c, booking_id, staff_id)
            cached = self._idempotent_response(c, action_id, event, request_payload)
            if cached:
                return cached
            if booking["status"] != expected:
                raise BookingError("INVALID_STATE_TRANSITION", f"Booking phải ở trạng thái {expected}.")
            now = iso(self.now())
            timestamp_sql = f",{timestamp_column}=?" if timestamp_column else ""
            params = (target, now, now, booking_id) if timestamp_column else (target, now, booking_id)
            c.execute(f"UPDATE bookings SET status=?{timestamp_sql},version=version+1,updated_at=? WHERE id=?", params)
            self._event(
                c, booking_id, event, "staff", {"staff_id": staff_id, "note": note} if note else {"staff_id": staff_id}
            )
            response = {"booking_id": booking_id, "status": target, "updated_at": now}
            self._save_idempotency(c, action_id, event, request_payload, response, now)
            return response

    @staticmethod
    def _parse_time(value):
        return parse_utc(value)
