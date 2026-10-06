from __future__ import annotations

import json
from datetime import timedelta
from typing import Any

from src.services.booking.common import iso, new_id, parse_utc

from .auth import InternalPrincipal, InternalRole
from .base import InternalPortalMixin
from .errors import InternalPortalError

ASSIGNMENT_ROLE = "test_drive_consultant"
BOOKING_TRANSITIONS = {
    "confirmed": {"checked_in", "cancelled", "no_show"},
    "checked_in": {"completed"},
}
BOOKING_TIMESTAMPS = {
    "checked_in": "checked_in_at",
    "cancelled": "cancelled_at",
    "completed": "completed_at",
    "no_show": "no_show_at",
}
VEHICLE_STATUS_TRANSITIONS = {
    "available": {"charging", "maintenance", "out_of_service", "in_use"},
    "charging": {"available", "maintenance", "out_of_service"},
    "maintenance": {"available", "out_of_service"},
    "out_of_service": {"available", "maintenance"},
    "in_use": {"available", "maintenance", "out_of_service"},
}


def time_ranges_overlap(start_a: str, end_a: str, start_b: str, end_b: str) -> bool:
    return parse_utc(start_a) < parse_utc(end_b) and parse_utc(end_a) > parse_utc(start_b)


class InternalOperationsMixin(InternalPortalMixin):
    """Scoped operational commands shared by manager and operations admin."""

    def _booking_for_operation(self, connection, principal: InternalPrincipal, booking_id: str):
        row = connection.execute(
            "SELECT b.*,s.showroom_id,s.start_at,s.end_at,s.demo_vehicle_id FROM bookings b "
            "JOIN test_drive_slots s ON s.id=b.slot_id WHERE b.id=?",
            (booking_id,),
        ).fetchone()
        if not row:
            raise InternalPortalError("BOOKING_NOT_FOUND", "Không tìm thấy booking.", status_code=404)
        self._assert_scope(principal, row["showroom_id"])
        return row

    def assign_booking(self, principal: InternalPrincipal, booking_id: str, *, staff_id: str) -> dict:
        self.require_roles(principal, InternalRole.SHOWROOM_MANAGER, InternalRole.OPERATIONS_ADMIN)
        now = iso(self.now())
        with self.db.transaction(immediate=True) as connection:
            booking = self._booking_for_operation(connection, principal, booking_id)
            if booking["status"] not in {"confirmed", "checked_in"}:
                raise InternalPortalError(
                    "BOOKING_NOT_ASSIGNABLE",
                    "Chỉ booking đã xác nhận hoặc đã check-in mới có thể phân công.",
                    status_code=409,
                )
            self._assert_staff_showroom(connection, staff_id, booking["showroom_id"])
            unavailable = any(
                time_ranges_overlap(
                    row["start_at"], row["end_at"], booking["start_at"], booking["end_at"]
                )
                for row in connection.execute(
                    "SELECT start_at,end_at FROM staff_unavailability WHERE sales_staff_id=?",
                    (staff_id,),
                )
            )
            conflicting_assignment = any(
                time_ranges_overlap(
                    row["start_at"], row["end_at"], booking["start_at"], booking["end_at"]
                )
                for row in connection.execute(
                    "SELECT other.start_at,other.end_at FROM slot_sales_assignments a "
                    "JOIN test_drive_slots other ON other.id=a.slot_id "
                    "WHERE a.sales_staff_id=? AND a.assignment_role=? AND a.status='assigned' AND other.id<>? "
                    "ORDER BY other.start_at",
                    (staff_id, ASSIGNMENT_ROLE, booking["slot_id"]),
                )
            )
            if unavailable or conflicting_assignment:
                raise InternalPortalError(
                    "STAFF_UNAVAILABLE",
                    "Không thể phân công vì nhân viên không khả dụng trong khung giờ này.",
                    status_code=409,
                )
            previous = connection.execute(
                "SELECT sales_staff_id FROM slot_sales_assignments WHERE slot_id=? "
                "AND assignment_role=? AND status='assigned' ORDER BY created_at LIMIT 1",
                (booking["slot_id"], ASSIGNMENT_ROLE),
            ).fetchone()
            connection.execute(
                "UPDATE slot_sales_assignments SET status='reassigned',updated_at=? WHERE slot_id=? "
                "AND assignment_role=? AND status='assigned' AND sales_staff_id<>?",
                (now, booking["slot_id"], ASSIGNMENT_ROLE, staff_id),
            )
            existing = connection.execute(
                "SELECT id FROM slot_sales_assignments WHERE slot_id=? AND sales_staff_id=? AND assignment_role=?",
                (booking["slot_id"], staff_id, ASSIGNMENT_ROLE),
            ).fetchone()
            if existing:
                connection.execute(
                    "UPDATE slot_sales_assignments SET status='assigned',updated_at=? WHERE id=?",
                    (now, existing["id"]),
                )
            else:
                connection.execute(
                    "INSERT INTO slot_sales_assignments(id,slot_id,sales_staff_id,assignment_role,status,created_at,updated_at) "
                    "VALUES(?,?,?,?,?,?,?)",
                    (new_id("assign"), booking["slot_id"], staff_id, ASSIGNMENT_ROLE, "assigned", now, now),
                )
            connection.execute(
                "UPDATE bookings SET assigned_sales_staff_id=?,version=version+1,updated_at=? WHERE id=?",
                (staff_id, now, booking_id),
            )
            connection.execute(
                "INSERT INTO booking_events(id,booking_id,event_type,actor_type,actor_id,payload_json,created_at) "
                "VALUES(?,?,?,?,?,?,?)",
                (
                    new_id("evt"),
                    booking_id,
                    "booking_staff_assigned",
                    "internal_user",
                    principal.user_id,
                    json.dumps({"staff_id": staff_id}, separators=(",", ":")),
                    now,
                ),
            )
            self._audit(
                connection,
                principal,
                "booking.staff_assigned",
                "booking",
                booking_id,
                booking["showroom_id"],
                {
                    "old_staff_id": previous["sales_staff_id"] if previous else None,
                    "new_staff_id": staff_id,
                },
            )
        return {"booking_id": booking_id, "assigned_staff_id": staff_id, "updated_at": now}

    def record_booking_license_check(
        self,
        principal: InternalPrincipal,
        booking_id: str,
        *,
        original_document_presented: bool,
        license_class_matches: bool,
        is_currently_valid: bool,
        result: str,
        rejection_reason: str | None = None,
    ) -> dict:
        self.require_roles(principal, InternalRole.SHOWROOM_MANAGER, InternalRole.OPERATIONS_ADMIN)
        if result not in {"verified", "rejected"}:
            raise InternalPortalError("INVALID_INPUT", "Kết quả kiểm tra GPLX không hợp lệ.")
        if result == "verified" and not all(
            (original_document_presented, license_class_matches, is_currently_valid)
        ):
            raise InternalPortalError("INVALID_INPUT", "Không thể xác minh GPLX khi điều kiện chưa đạt.")
        if result == "rejected" and not (rejection_reason or "").strip():
            raise InternalPortalError("REJECTION_REASON_REQUIRED", "Cần nhập lý do từ chối GPLX.")
        now = iso(self.now())
        with self.db.transaction(immediate=True) as connection:
            booking = self._booking_for_operation(connection, principal, booking_id)
            if booking["status"] != "confirmed":
                raise InternalPortalError(
                    "INVALID_STATE_TRANSITION", "Booking phải ở trạng thái confirmed.", status_code=409
                )
            assigned = connection.execute(
                "SELECT a.sales_staff_id FROM slot_sales_assignments a JOIN sales_staff s ON s.id=a.sales_staff_id "
                "WHERE a.slot_id=? AND a.assignment_role=? AND a.status='assigned' "
                "AND s.status='active' AND s.is_active=1 LIMIT 1",
                (booking["slot_id"], ASSIGNMENT_ROLE),
            ).fetchone()
            if not assigned:
                raise InternalPortalError(
                    "STAFF_ASSIGNMENT_REQUIRED", "Cần phân công nhân viên trước khi kiểm tra GPLX.", status_code=409
                )
            connection.execute(
                "UPDATE booking_driver_details SET license_check_status=?,checked_at=?,checked_by=?,"
                "rejection_reason=?,updated_at=? WHERE booking_id=?",
                (
                    result,
                    now,
                    assigned["sales_staff_id"],
                    (rejection_reason or "").strip() if result == "rejected" else None,
                    now,
                    booking_id,
                ),
            )
            self._audit(
                connection,
                principal,
                f"booking.license_{result}",
                "booking",
                booking_id,
                booking["showroom_id"],
                {"checked_by_staff_id": assigned["sales_staff_id"]},
            )
        return {
            "booking_id": booking_id,
            "license_check_status": result,
            "checked_by": assigned["sales_staff_id"],
            "checked_at": now,
        }

    def transition_booking(
        self,
        principal: InternalPrincipal,
        booking_id: str,
        *,
        target_status: str,
        note: str | None = None,
    ) -> dict:
        self.require_roles(principal, InternalRole.SHOWROOM_MANAGER, InternalRole.OPERATIONS_ADMIN)
        if target_status not in BOOKING_TIMESTAMPS:
            raise InternalPortalError("INVALID_BOOKING_STATUS", "Trạng thái booking không được phép cập nhật.")
        now_value = self.now()
        now = iso(now_value)
        with self.db.transaction(immediate=True) as connection:
            booking = self._booking_for_operation(connection, principal, booking_id)
            if target_status not in BOOKING_TRANSITIONS.get(booking["status"], set()):
                raise InternalPortalError(
                    "INVALID_STATE_TRANSITION",
                    f"Không thể chuyển booking từ {booking['status']} sang {target_status}.",
                    status_code=409,
                )
            if target_status == "checked_in":
                detail = connection.execute(
                    "SELECT license_check_status FROM booking_driver_details WHERE booking_id=?", (booking_id,)
                ).fetchone()
                if not detail or detail["license_check_status"] != "verified":
                    raise InternalPortalError(
                        "LICENSE_NOT_VERIFIED", "GPLX chưa được xác minh.", status_code=409
                    )
                start = parse_utc(booking["start_at"])
                if not start - timedelta(minutes=60) <= now_value <= start + timedelta(minutes=30):
                    raise InternalPortalError(
                        "INVALID_STATE_TRANSITION", "Booking nằm ngoài cửa sổ check-in.", status_code=409
                    )
            if target_status == "no_show" and now_value <= parse_utc(booking["start_at"]) + timedelta(minutes=30):
                raise InternalPortalError(
                    "INVALID_STATE_TRANSITION", "Chưa qua grace period để đánh dấu no-show.", status_code=409
                )
            timestamp = BOOKING_TIMESTAMPS[target_status]
            cancellation_reason = (note or "").strip() if target_status == "cancelled" else None
            connection.execute(
                f"UPDATE bookings SET status=?,{timestamp}=?,cancellation_reason=?,version=version+1,updated_at=? WHERE id=?",
                (target_status, now, cancellation_reason, now, booking_id),
            )
            if target_status == "cancelled":
                connection.execute(
                    "UPDATE test_drive_slots SET status='available',current_booking_id=NULL,held_until=NULL,updated_at=? "
                    "WHERE id=? AND current_booking_id=?",
                    (now, booking["slot_id"], booking_id),
                )
                connection.execute(
                    "UPDATE notification_jobs SET status='cancelled',updated_at=? "
                    "WHERE booking_id=? AND status IN ('pending','processing','retrying')",
                    (now, booking_id),
                )
            connection.execute(
                "INSERT INTO booking_events(id,booking_id,event_type,actor_type,actor_id,payload_json,created_at) "
                "VALUES(?,?,?,?,?,?,?)",
                (
                    new_id("evt"),
                    booking_id,
                    f"booking_{target_status}",
                    "internal_user",
                    principal.user_id,
                    json.dumps({"target_status": target_status}, separators=(",", ":")),
                    now,
                ),
            )
            self._audit(
                connection,
                principal,
                f"booking.{target_status}",
                "booking",
                booking_id,
                booking["showroom_id"],
                {"old_status": booking["status"], "new_status": target_status},
            )
        return {"booking_id": booking_id, "status": target_status, "updated_at": now}

    def update_shift(
        self,
        principal: InternalPrincipal,
        shift_id: str,
        *,
        start_at: str | None = None,
        end_at: str | None = None,
        status: str | None = None,
    ) -> dict:
        self.require_roles(principal, InternalRole.SHOWROOM_MANAGER, InternalRole.OPERATIONS_ADMIN)
        if status is not None and status not in {"scheduled", "cancelled"}:
            raise InternalPortalError("INVALID_SHIFT_STATUS", "Trạng thái ca làm không hợp lệ.")
        with self.db.transaction(immediate=True) as connection:
            current = connection.execute("SELECT * FROM staff_shifts WHERE id=?", (shift_id,)).fetchone()
            if not current:
                raise InternalPortalError("SHIFT_NOT_FOUND", "Không tìm thấy ca làm.", status_code=404)
            self._assert_scope(principal, current["showroom_id"])
            new_start = start_at or current["start_at"]
            new_end = end_at or current["end_at"]
            if parse_utc(new_end) <= parse_utc(new_start):
                raise InternalPortalError("INVALID_TIME_RANGE", "Giờ kết thúc phải sau giờ bắt đầu.")
            new_status = status or current["status"]
            if new_status == "scheduled":
                conflict = any(
                    time_ranges_overlap(row["start_at"], row["end_at"], new_start, new_end)
                    for row in connection.execute(
                        "SELECT start_at,end_at FROM staff_shifts WHERE sales_staff_id=? "
                        "AND id<>? AND status='scheduled'",
                        (current["sales_staff_id"], shift_id),
                    )
                )
                unavailable = any(
                    time_ranges_overlap(row["start_at"], row["end_at"], new_start, new_end)
                    for row in connection.execute(
                        "SELECT start_at,end_at FROM staff_unavailability WHERE sales_staff_id=?",
                        (current["sales_staff_id"],),
                    )
                )
                if conflict or unavailable:
                    raise InternalPortalError(
                        "SCHEDULE_CONFLICT", "Ca làm trùng lịch hoặc thời gian không khả dụng.", status_code=409
                    )
            now = iso(self.now())
            connection.execute(
                "UPDATE staff_shifts SET start_at=?,end_at=?,status=?,updated_at=? WHERE id=?",
                (new_start, new_end, new_status, now, shift_id),
            )
            self._audit(
                connection,
                principal,
                "shift.updated",
                "staff_shift",
                shift_id,
                current["showroom_id"],
                {
                    "old": {"start_at": current["start_at"], "end_at": current["end_at"], "status": current["status"]},
                    "new": {"start_at": new_start, "end_at": new_end, "status": new_status},
                },
            )
            updated = connection.execute("SELECT * FROM staff_shifts WHERE id=?", (shift_id,)).fetchone()
        return dict(updated)

    def list_operating_hours(self, principal: InternalPrincipal, *, showroom_id: str) -> list[dict]:
        self.require_roles(principal, InternalRole.SHOWROOM_MANAGER, InternalRole.OPERATIONS_ADMIN)
        self._assert_scope(principal, showroom_id)
        with self.db.connect() as connection:
            return [
                dict(row)
                for row in connection.execute(
                    "SELECT * FROM showroom_operating_hours WHERE showroom_id=? ORDER BY day_of_week",
                    (showroom_id,),
                )
            ]

    def update_operating_hour(
        self,
        principal: InternalPrincipal,
        *,
        showroom_id: str,
        day_of_week: int,
        open_time: str | None,
        close_time: str | None,
        is_closed: bool,
    ) -> dict:
        self.require_roles(principal, InternalRole.SHOWROOM_MANAGER, InternalRole.OPERATIONS_ADMIN)
        self._assert_scope(principal, showroom_id)
        if day_of_week not in range(7):
            raise InternalPortalError("INVALID_DAY", "Ngày trong tuần phải nằm trong khoảng 0–6.")
        if not is_closed and (not open_time or not close_time or open_time >= close_time):
            raise InternalPortalError("INVALID_OPERATING_HOURS", "Giờ mở cửa phải trước giờ đóng cửa.")
        now = iso(self.now())
        with self.db.transaction(immediate=True) as connection:
            current = connection.execute(
                "SELECT * FROM showroom_operating_hours WHERE showroom_id=? AND day_of_week=?",
                (showroom_id, day_of_week),
            ).fetchone()
            values = (None, None) if is_closed else (open_time, close_time)
            if current:
                connection.execute(
                    "UPDATE showroom_operating_hours SET open_time=?,close_time=?,is_closed=?,updated_at=? WHERE id=?",
                    (*values, int(is_closed), now, current["id"]),
                )
                record_id = current["id"]
            else:
                record_id = new_id("hours")
                connection.execute(
                    "INSERT INTO showroom_operating_hours(id,showroom_id,day_of_week,open_time,close_time,is_closed,created_at,updated_at) "
                    "VALUES(?,?,?,?,?,?,?,?)",
                    (record_id, showroom_id, day_of_week, *values, int(is_closed), now, now),
                )
            self._audit(
                connection,
                principal,
                "showroom.operating_hours_updated",
                "showroom_operating_hours",
                record_id,
                showroom_id,
                {"day_of_week": day_of_week, "open_time": values[0], "close_time": values[1], "is_closed": is_closed},
            )
            updated = connection.execute(
                "SELECT * FROM showroom_operating_hours WHERE id=?", (record_id,)
            ).fetchone()
        return dict(updated)

    def list_vehicle_unavailability(
        self, principal: InternalPrincipal, *, showroom_id: str | None = None, vehicle_id: str | None = None
    ) -> list[dict]:
        self.require_roles(principal, InternalRole.SHOWROOM_MANAGER, InternalRole.OPERATIONS_ADMIN)
        params: list[Any] = []
        where = ["1=1"]
        if showroom_id:
            self._assert_scope(principal, showroom_id)
            where.append("u.showroom_id=?")
            params.append(showroom_id)
        elif principal.role is InternalRole.SHOWROOM_MANAGER:
            where.append("u.showroom_id=?")
            params.append(principal.showroom_ids[0])
        if vehicle_id:
            where.append("u.demo_vehicle_id=?")
            params.append(vehicle_id)
        with self.db.connect() as connection:
            return [
                dict(row)
                for row in connection.execute(
                    "SELECT u.*,d.asset_code FROM vehicle_unavailability u "
                    "JOIN demo_vehicles d ON d.id=u.demo_vehicle_id WHERE "
                    + " AND ".join(where)
                    + " ORDER BY u.start_at DESC LIMIT 500",
                    params,
                )
            ]

    def create_vehicle_unavailability(
        self,
        principal: InternalPrincipal,
        vehicle_id: str,
        *,
        start_at: str,
        end_at: str,
        reason: str,
    ) -> dict:
        self.require_roles(principal, InternalRole.SHOWROOM_MANAGER, InternalRole.OPERATIONS_ADMIN)
        if parse_utc(end_at) <= parse_utc(start_at):
            raise InternalPortalError("INVALID_TIME_RANGE", "Giờ kết thúc phải sau giờ bắt đầu.")
        if not reason.strip():
            raise InternalPortalError("REASON_REQUIRED", "Cần nhập lý do khóa xe.")
        now = iso(self.now())
        record_id = new_id("vehicle_unavailable")
        with self.db.transaction(immediate=True) as connection:
            vehicle = connection.execute("SELECT * FROM demo_vehicles WHERE id=?", (vehicle_id,)).fetchone()
            if not vehicle:
                raise InternalPortalError("VEHICLE_NOT_FOUND", "Không tìm thấy xe demo.", status_code=404)
            self._assert_scope(principal, vehicle["showroom_id"])
            conflict = any(
                time_ranges_overlap(row["start_at"], row["end_at"], start_at, end_at)
                for row in connection.execute(
                    "SELECT s.start_at,s.end_at FROM test_drive_slots s "
                    "LEFT JOIN bookings b ON b.id=s.current_booking_id WHERE s.demo_vehicle_id=? "
                    "AND (s.status='held' OR (s.status='booked' AND b.status IN ('confirmed','checked_in')))",
                    (vehicle_id,),
                )
            )
            if conflict:
                raise InternalPortalError(
                    "VEHICLE_BOOKING_CONFLICT",
                    "Không thể khóa xe vì xe có booking hoặc hold trong thời gian này.",
                    status_code=409,
                )
            connection.execute(
                "INSERT INTO vehicle_unavailability(id,demo_vehicle_id,showroom_id,start_at,end_at,reason,created_by,created_at,updated_at) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                (record_id, vehicle_id, vehicle["showroom_id"], start_at, end_at, reason.strip(), principal.user_id, now, now),
            )
            slot_ids = [
                row["id"]
                for row in connection.execute(
                    "SELECT id,start_at,end_at FROM test_drive_slots "
                    "WHERE demo_vehicle_id=? AND status='available'",
                    (vehicle_id,),
                )
                if time_ranges_overlap(row["start_at"], row["end_at"], start_at, end_at)
            ]
            connection.executemany(
                "UPDATE test_drive_slots SET status='blocked',block_reason=?,updated_at=? WHERE id=?",
                [(f"vehicle_unavailability:{record_id}", now, slot_id) for slot_id in slot_ids],
            )
            self._audit(
                connection,
                principal,
                "vehicle.unavailability_created",
                "vehicle_unavailability",
                record_id,
                vehicle["showroom_id"],
                {"vehicle_id": vehicle_id, "start_at": start_at, "end_at": end_at, "reason": reason.strip()},
            )
        return {
            "id": record_id,
            "vehicle_id": vehicle_id,
            "showroom_id": vehicle["showroom_id"],
            "start_at": start_at,
            "end_at": end_at,
            "reason": reason.strip(),
        }

    def delete_vehicle_unavailability(self, principal: InternalPrincipal, record_id: str) -> None:
        self.require_roles(principal, InternalRole.SHOWROOM_MANAGER, InternalRole.OPERATIONS_ADMIN)
        now = iso(self.now())
        with self.db.transaction(immediate=True) as connection:
            record = connection.execute(
                "SELECT * FROM vehicle_unavailability WHERE id=?", (record_id,)
            ).fetchone()
            if not record:
                raise InternalPortalError("UNAVAILABILITY_NOT_FOUND", "Không tìm thấy khoảng khóa xe.", status_code=404)
            self._assert_scope(principal, record["showroom_id"])
            connection.execute("DELETE FROM vehicle_unavailability WHERE id=?", (record_id,))
            connection.execute(
                "UPDATE test_drive_slots SET status='available',block_reason=NULL,updated_at=? "
                "WHERE demo_vehicle_id=? AND status='blocked' AND block_reason=?",
                (now, record["demo_vehicle_id"], f"vehicle_unavailability:{record_id}"),
            )
            self._audit(
                connection,
                principal,
                "vehicle.unavailability_removed",
                "vehicle_unavailability",
                record_id,
                record["showroom_id"],
                {"vehicle_id": record["demo_vehicle_id"]},
            )

    def validate_vehicle_status_transition(self, current: str, target: str) -> None:
        if current == target:
            return
        if target not in VEHICLE_STATUS_TRANSITIONS.get(current, set()):
            raise InternalPortalError(
                "INVALID_VEHICLE_STATUS_TRANSITION",
                f"Không thể chuyển trạng thái xe từ {current} sang {target}.",
                status_code=409,
            )
