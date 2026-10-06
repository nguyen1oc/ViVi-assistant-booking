from __future__ import annotations

import json
import secrets
from datetime import timedelta
from zoneinfo import ZoneInfo

from src.database.redis_client import redis_client
from src.services.booking.base import BookingBase
from src.services.booking.common import iso, new_id, normalize_phone, parse_utc, person_patch_validation_error
from src.services.booking.errors import BookingError

_id = new_id
VIETNAM_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
HOLD_TTL_SECONDS = 5 * 60


class LifecycleService(BookingBase):
    def hold_slot(
        self,
        slot_id: str,
        ui_action_id: str,
        *,
        ttl_seconds: int = HOLD_TTL_SECONDS,
        source_channel: str = "web",
        _operation: str = "hold_slot",
        _idempotency_payload: dict | None = None,
    ) -> dict:
        if ttl_seconds != HOLD_TTL_SECONDS:
            raise BookingError("INVALID_INPUT", "Hold TTL được cố định ở 300 giây.")
        request_payload = _idempotency_payload or {"slot_id": slot_id, "source_channel": source_channel}
        with self.db.transaction(immediate=True) as c:
            cached = self._idempotent_response(c, ui_action_id, _operation, request_payload)
            if cached:
                return cached
            slot_query = (
                "SELECT s.*,d.is_active vehicle_active,d.operational_status,d.battery_soc,d.minimum_booking_soc,"
                "v.required_license_class,v.id resolved_model_id,v.code resolved_model_code,v.name resolved_model_name "
                "FROM test_drive_slots s JOIN demo_vehicles d ON d.id=s.demo_vehicle_id "
                "JOIN vehicle_variants x ON x.id=d.variant_id JOIN vehicle_models v ON v.id=x.model_id WHERE s.id=?"
                + (" FOR UPDATE OF s" if c.dialect == "postgres" else "")
            )
            slot = c.execute(slot_query, (slot_id,)).fetchone()
            now = self.now()
            if (
                slot
                and slot["status"] == "held"
                and slot["held_until"]
                and parse_utc(slot["held_until"]) <= parse_utc(now)
                and slot["current_booking_id"]
            ):
                expired_booking = c.execute(
                    "SELECT * FROM bookings WHERE id=?" + (" FOR UPDATE" if c.dialect == "postgres" else ""),
                    (slot["current_booking_id"],),
                ).fetchone()
                if (
                    expired_booking
                    and expired_booking["status"] == "held"
                    and parse_utc(expired_booking["hold_expires_at"]) <= parse_utc(now)
                ):
                    self._expire_hold_in_transaction(c, expired_booking)
                    slot = c.execute(slot_query, (slot_id,)).fetchone()
            if not slot or slot["status"] != "available":
                raise BookingError("SLOT_NO_LONGER_AVAILABLE", "Khung giờ này không còn khả dụng.", retryable=True)
            if parse_utc(slot["start_at"]) <= parse_utc(now):
                raise BookingError("SLOT_NO_LONGER_AVAILABLE", "Slot đã bắt đầu hoặc đã qua.", retryable=True)
            if parse_utc(slot["start_at"]) > parse_utc(
                now + timedelta(days=self.booking_advance_window_days)
            ):
                raise BookingError(
                    "SLOT_NO_LONGER_AVAILABLE",
                    f"Booking is limited to {self.booking_advance_window_days} days in advance.",
                    retryable=True,
                )
            if not slot["vehicle_active"] or slot["operational_status"] != "available":
                raise BookingError("VEHICLE_NOT_READY", "Xe demo hiện không sẵn sàng.", retryable=True)
            if slot["battery_soc"] is None or slot["battery_soc"] < slot["minimum_booking_soc"]:
                raise BookingError("VEHICLE_NOT_READY", "Pin xe demo chưa đạt ngưỡng phục vụ.", retryable=True)
            overlap = c.execute(
                "SELECT 1 FROM test_drive_slots WHERE demo_vehicle_id=? AND id<>? AND start_at<? AND end_at>? "
                "AND (status IN ('booked','blocked') OR (status='held' AND (held_until IS NULL OR held_until>?))) "
                "LIMIT 1",
                (slot["demo_vehicle_id"], slot_id, slot["end_at"], slot["start_at"], iso(now)),
            ).fetchone()
            if overlap:
                raise BookingError("SLOT_NO_LONGER_AVAILABLE", "Xe demo đã có lịch trùng.", retryable=True)
            staff_candidates, staff_capacity_tracked = self._available_sales_staff(
                c,
                showroom_id=slot["showroom_id"],
                start_at=slot["start_at"],
                end_at=slot["end_at"],
                slot_id=slot_id,
                lock=True,
            )
            if staff_capacity_tracked and not staff_candidates:
                raise BookingError(
                    "STAFF_NOT_AVAILABLE",
                    "Không còn tư vấn viên khả dụng trong khung giờ này.",
                    retryable=True,
                )
            expires, booking_id = now + timedelta(seconds=ttl_seconds), _id("bkg")
            if staff_candidates:
                self._assign_sales_staff_to_slot(
                    c,
                    slot_id=slot_id,
                    staff_id=str(staff_candidates[0]["id"]),
                    now=iso(now),
                )
            c.execute(
                "INSERT INTO bookings(id,slot_id,status,held_at,hold_expires_at,source_channel,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                (booking_id, slot_id, "held", iso(now), iso(expires), source_channel, iso(now), iso(now)),
            )
            c.execute(
                "UPDATE test_drive_slots SET status='held',held_until=?,current_booking_id=?,updated_at=? WHERE id=?",
                (iso(expires), booking_id, iso(now), slot_id),
            )
            redis_client.hold_slot(slot_id, booking_id, ttl_seconds=ttl_seconds)
            c.execute(
                "INSERT INTO booking_driver_details(booking_id,required_license_class,created_at,updated_at) VALUES(?,?,?,?)",
                (booking_id, slot["required_license_class"], iso(now), iso(now)),
            )
            c.execute(
                "INSERT INTO notification_plans(booking_id,created_at,updated_at) VALUES(?,?,?)",
                (booking_id, iso(now), iso(now)),
            )
            self._event(c, booking_id, "slot_held", "user", {"slot_id": slot_id})
            showroom_row = c.execute("SELECT * FROM showrooms WHERE id=?", (slot["showroom_id"],)).fetchone()
            showroom = dict(showroom_row) if showroom_row else None
            dt = parse_utc(slot["start_at"]).astimezone(VIETNAM_TZ)
            weekdays_vi = {
                0: "Thứ 2", 1: "Thứ 3", 2: "Thứ 4", 3: "Thứ 5", 4: "Thứ 6", 5: "Thứ 7", 6: "Chủ nhật"
            }
            slot_date = f"{weekdays_vi[dt.weekday()]}, {dt.strftime('%d/%m')}"
            slot_time = dt.strftime("%H:%M")
            result = {
                "booking_id": booking_id,
                "status": "held",
                "version": 1,
                "hold_expires_at": iso(expires),
                "remaining_seconds": ttl_seconds,
                "showroom": showroom,
                "resolved_vehicle": {
                    "id": slot["resolved_model_id"],
                    "code": slot["resolved_model_code"],
                    "name": slot["resolved_model_name"],
                },
                "slot_id": slot_id,
                "slot_date": slot_date,
                "slot_time": slot_time,
                "start_at": slot["start_at"],
                "end_at": slot["end_at"],
            }
            self._save_idempotency(c, ui_action_id, _operation, request_payload, result, iso(now))
            return result

    def release_hold(self, booking_id: str) -> dict:
        with self.db.transaction(immediate=True) as c:
            b = c.execute("SELECT * FROM bookings WHERE id=?", (booking_id,)).fetchone()
            if b and b["status"] == "held":
                slot_id = b["slot_id"]
                if slot_id:
                    c.execute(
                        "SELECT id FROM test_drive_slots WHERE id=?"
                        + (" FOR UPDATE" if c.dialect == "postgres" else ""),
                        (slot_id,),
                    ).fetchone()
                b = c.execute(
                    "SELECT * FROM bookings WHERE id=?" + (" FOR UPDATE" if c.dialect == "postgres" else ""),
                    (booking_id,),
                ).fetchone()
                if b and b["status"] == "held":
                    now = iso(self.now())
                    c.execute("UPDATE bookings SET status='cancelled', updated_at=? WHERE id=?", (now, booking_id))
                    released_slot = c.execute(
                        "UPDATE test_drive_slots SET status='available', current_booking_id=NULL, held_until=NULL, "
                        "updated_at=? WHERE id=? AND current_booking_id=? AND status='held'",
                        (now, slot_id, booking_id),
                    )
                    if slot_id and released_slot.rowcount:
                        redis_client.delete_slot_hold(slot_id)
                    self._event(c, booking_id, "hold_released", "user", {})
            return {"booking_id": booking_id, "status": "released"}

    def _draft(self, c, booking_id: str, *, require_held: bool = True) -> dict:
        booking = self._row(c.execute("SELECT * FROM bookings WHERE id=?", (booking_id,)).fetchone())
        if not booking:
            raise BookingError("BOOKING_DRAFT_NOT_AVAILABLE", "Booking draft không khả dụng.")
        if require_held and booking["status"] != "held":
            raise BookingError("BOOKING_DRAFT_NOT_AVAILABLE", "Booking draft không khả dụng.")
        if require_held and parse_utc(booking["hold_expires_at"]) <= parse_utc(self.now()):
            raise BookingError("HOLD_EXPIRED", "Hold đã hết hạn.")
        booking["booker"] = (
            self._row(c.execute("SELECT * FROM people WHERE id=?", (booking["booker_person_id"],)).fetchone())
            if booking["booker_person_id"]
            else None
        )
        booking["driver"] = (
            self._row(c.execute("SELECT * FROM people WHERE id=?", (booking["driver_person_id"],)).fetchone())
            if booking["driver_person_id"]
            else None
        )
        booking["license_declaration"] = self._row(
            c.execute("SELECT * FROM booking_driver_details WHERE booking_id=?", (booking_id,)).fetchone()
        )
        booking["notification_plan"] = self._row(
            c.execute("SELECT * FROM notification_plans WHERE booking_id=?", (booking_id,)).fetchone()
        )
        missing = []
        for role in ("booker", "driver"):
            if not booking[role]:
                missing.append(role)
            else:
                if not booking[role]["full_name"]:
                    missing.append(f"{role}.full_name")
                if not booking[role]["email"]:
                    missing.append(f"{role}.email")
        lic = booking["license_declaration"] or {}
        if "has_driving_license" in lic and lic["has_driving_license"] is not None:
            lic["has_driving_license"] = bool(lic["has_driving_license"])
        if "validity_acknowledged" in lic:
            lic["validity_acknowledged"] = bool(lic["validity_acknowledged"])
        if lic.get("has_driving_license") is not True and lic.get("has_driving_license") != 1:
            missing.append("license.has_driving_license")
        remaining = max(0, int((parse_utc(booking["hold_expires_at"]) - parse_utc(self.now())).total_seconds()))
        slot_row = c.execute("SELECT * FROM test_drive_slots WHERE id=?", (booking["slot_id"],)).fetchone()
        if slot_row:
            slot = dict(slot_row)
            showroom_row = c.execute("SELECT * FROM showrooms WHERE id=?", (slot["showroom_id"],)).fetchone()
            booking["showroom"] = dict(showroom_row) if showroom_row else None
            booking["slot_id"] = slot["id"]
            dt = parse_utc(slot["start_at"]).astimezone(VIETNAM_TZ)
            weekdays_vi = {
                0: "Thứ 2",
                1: "Thứ 3",
                2: "Thứ 4",
                3: "Thứ 5",
                4: "Thứ 6",
                5: "Thứ 7",
                6: "Chủ nhật"
            }
            booking["slot_date"] = f"{weekdays_vi[dt.weekday()]}, {dt.strftime('%d/%m')}"
            booking["slot_time"] = dt.strftime("%H:%M")
        else:
            booking["showroom"] = None
            booking["slot_date"] = "Ngày đã chọn"
            booking["slot_time"] = "21:00 - 22:00"

        booking.update(
            missing_required_fields=missing,
            validation_warnings=[],
            remaining_seconds=remaining,
            is_ready_to_confirm=not missing and remaining > 0,
        )
        return booking

    def get_booking_draft(self, booking_id: str) -> dict:
        if self._expire_hold_if_due(booking_id):
            raise BookingError("HOLD_EXPIRED", "Hold đã hết hạn.")
        with self.db.transaction(immediate=True) as c:
            return self._draft(c, booking_id)

    def _expire_hold_if_due(self, booking_id: str) -> bool:
        """Durably release an expired hold in its own complete transaction."""
        with self.db.transaction(immediate=True) as c:
            booking = c.execute(
                "SELECT * FROM bookings WHERE id=?" + (" FOR UPDATE" if c.dialect == "postgres" else ""),
                (booking_id,),
            ).fetchone()
            if (
                not booking
                or booking["status"] != "held"
                or parse_utc(booking["hold_expires_at"]) > parse_utc(self.now())
            ):
                return False
            self._expire_hold_in_transaction(c, booking)
            return True

    def _expire_hold_in_transaction(self, c, booking) -> None:
        now = iso(self.now())
        c.execute(
            "UPDATE bookings SET status='expired',version=version+1,updated_at=? WHERE id=? AND status='held'",
            (now, booking["id"]),
        )
        c.execute(
            "UPDATE test_drive_slots SET status='available',held_until=NULL,current_booking_id=NULL,updated_at=? "
            "WHERE id=? AND current_booking_id=? AND status='held'",
            (now, booking["slot_id"], booking["id"]),
        )
        self._event(c, booking["id"], "hold_expired")

    def update_booking_draft(
        self,
        booking_id: str,
        *,
        booker_patch=None,
        driver_patch=None,
        driver_same_as_booker: bool = False,
        license_patch=None,
        notification_plan_patch=None,
        expected_version=None,
    ) -> dict:
        for patch in (booker_patch, None if driver_same_as_booker else driver_patch):
            validation_error = person_patch_validation_error(patch)
            if validation_error:
                raise BookingError("INVALID_INPUT", validation_error)
        if self._expire_hold_if_due(booking_id):
            raise BookingError("HOLD_EXPIRED", "Hold đã hết hạn.")
        with self.db.transaction(immediate=True) as c:
            b = c.execute("SELECT * FROM bookings WHERE id=?", (booking_id,)).fetchone()
            if not b:
                raise BookingError("BOOKING_NOT_FOUND", "Không tìm thấy booking.")
            if b["status"] != "held":
                raise BookingError("BOOKING_DRAFT_NOT_AVAILABLE", "Booking draft không khả dụng.")
            if parse_utc(b["hold_expires_at"]) <= parse_utc(self.now()):
                raise BookingError("HOLD_EXPIRED", "Hold đã hết hạn.")
            if expected_version is not None and b["version"] != expected_version:
                raise BookingError("VERSION_CONFLICT", "Draft đã được cập nhật ở nơi khác.", retryable=True)
            for role, patch in (("booker", booker_patch), ("driver", None if driver_same_as_booker else driver_patch)):
                if patch:
                    allowed = {
                        k: patch.get(k) for k in ("full_name", "phone", "email", "preferred_channel") if k in patch
                    }
                    current_pid = b[f"{role}_person_id"]
                    if role == "driver" and current_pid is not None and current_pid == b["booker_person_id"]:
                        # Changing a self-booking to on-behalf must preserve the
                        # Booker person and attach a new Driver person.
                        current_pid = None
                    if not current_pid and not allowed.get("full_name"):
                        raise BookingError("INVALID_INPUT", f"{role}.full_name là bắt buộc.")
                    pid = current_pid or _id("person")
                    now = iso(self.now())
                    if current_pid:
                        sets = ",".join(f"{k}=?" for k in allowed)
                        c.execute(f"UPDATE people SET {sets},updated_at=? WHERE id=?", (*allowed.values(), now, pid))
                        if "phone" in allowed:
                            c.execute(
                                "UPDATE people SET normalized_phone=? WHERE id=?",
                                (normalize_phone(allowed["phone"]), pid),
                            )
                        if "email" in allowed:
                            c.execute(
                                "UPDATE people SET normalized_email=? WHERE id=?",
                                ((allowed["email"] or "").lower() or None, pid),
                            )
                    else:
                        if not allowed.get("email"):
                            raise BookingError("INVALID_INPUT", f"{role}.email la bat buoc.")
                        c.execute(
                            "INSERT INTO people(id,full_name,phone,email,preferred_channel,normalized_phone,normalized_email,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
                            (
                                pid,
                                allowed["full_name"],
                                allowed.get("phone"),
                                allowed.get("email"),
                                allowed.get("preferred_channel", "email"),
                                normalize_phone(allowed.get("phone")),
                                (allowed.get("email") or "").lower() or None,
                                now,
                                now,
                            ),
                        )
                        if role == "driver":
                            c.execute(
                                "UPDATE booking_driver_details SET has_driving_license=NULL,declared_license_class=NULL,"
                                "validity_acknowledged=0,license_check_status='not_provided',checked_at=NULL,"
                                "checked_by=NULL,rejection_reason=NULL,updated_at=? WHERE booking_id=?",
                                (now, booking_id),
                            )
                        c.execute(f"UPDATE bookings SET {role}_person_id=? WHERE id=?", (pid, booking_id))
            if driver_same_as_booker:
                current_people = c.execute(
                    "SELECT booker_person_id,driver_person_id FROM bookings WHERE id=?", (booking_id,)
                ).fetchone()
                booker_id = current_people["booker_person_id"] if current_people else None
                if not booker_id:
                    raise BookingError("INVALID_INPUT", "Cần nhập thông tin Booker trước.")
                if current_people["driver_person_id"] != booker_id:
                    c.execute(
                        "UPDATE booking_driver_details SET has_driving_license=NULL,declared_license_class=NULL,"
                        "validity_acknowledged=0,license_check_status='not_provided',checked_at=NULL,checked_by=NULL,"
                        "rejection_reason=NULL,updated_at=? WHERE booking_id=?",
                        (iso(self.now()), booking_id),
                    )
                c.execute("UPDATE bookings SET driver_person_id=? WHERE id=?", (booker_id, booking_id))
            if license_patch:
                allowed = {}
                commitment_key = (
                    "has_valid_license_commitment"
                    if "has_valid_license_commitment" in license_patch
                    else "has_driving_license"
                )
                if commitment_key in license_patch:
                    commitment = bool(license_patch[commitment_key])
                    allowed["has_driving_license"] = int(commitment)
                    allowed["license_check_status"] = "declared" if commitment else "not_provided"
                    if not commitment:
                        allowed["declared_license_class"] = None
                        allowed["validity_acknowledged"] = 0
                for key in ("declared_license_class", "validity_acknowledged"):
                    if key in license_patch:
                        allowed[key] = (
                            int(bool(license_patch[key])) if key == "validity_acknowledged" else license_patch[key]
                        )
                if allowed:
                    c.execute(
                        "UPDATE booking_driver_details SET "
                        + ",".join(f"{k}=?" for k in allowed)
                        + ",updated_at=? WHERE booking_id=?",
                        (*allowed.values(), iso(self.now()), booking_id),
                    )
            if notification_plan_patch:
                allowed = {
                    k: v
                    for k, v in notification_plan_patch.items()
                    if k
                    in (
                        "copy_booker",
                        "zalo_enabled",
                        "sms_enabled",
                        "email_enabled",
                        "reminder_24h_enabled",
                        "reminder_2h_enabled",
                        "custom_plan_json",
                    )
                }
                if allowed:
                    c.execute(
                        "UPDATE notification_plans SET "
                        + ",".join(f"{k}=?" for k in allowed)
                        + ",updated_at=? WHERE booking_id=?",
                        (*allowed.values(), iso(self.now()), booking_id),
                    )
            c.execute("UPDATE bookings SET version=version+1,updated_at=? WHERE id=?", (iso(self.now()), booking_id))
            self._event(c, booking_id, "booking_draft_updated", "agent")
            return self._draft(c, booking_id)

    def confirm_booking(self, booking_id: str, ui_action_id: str, expected_version: int) -> dict:
        request_payload = {"booking_id": booking_id, "expected_version": expected_version}
        if self._expire_hold_if_due(booking_id):
            raise BookingError("HOLD_EXPIRED", "Giữ chỗ đã hết hạn.")
        with self.db.transaction(immediate=True) as c:
            cached = self._idempotent_response(c, ui_action_id, "confirm_booking", request_payload)
            if cached:
                return cached
            c.execute(
                "SELECT id FROM bookings WHERE id=?" + (" FOR UPDATE" if c.dialect == "postgres" else ""),
                (booking_id,),
            )
            draft = self._draft(c, booking_id)
            if draft["status"] != "held" or draft["remaining_seconds"] <= 0:
                raise BookingError("HOLD_EXPIRED", "Giữ chỗ đã hết hạn.")
            if draft["version"] != expected_version:
                raise BookingError("VERSION_CONFLICT", "Draft đã thay đổi.", retryable=True)
            if not draft["is_ready_to_confirm"]:
                raise BookingError("INVALID_INPUT", "Draft chưa đủ thông tin.")
            slot = c.execute(
                "SELECT s.*,d.is_active vehicle_active,d.operational_status,d.battery_soc,d.minimum_booking_soc "
                "FROM test_drive_slots s JOIN demo_vehicles d ON d.id=s.demo_vehicle_id WHERE s.id=?"
                + (" FOR UPDATE OF s" if c.dialect == "postgres" else ""),
                (draft["slot_id"],),
            ).fetchone()
            if slot["status"] != "held" or slot["current_booking_id"] != booking_id:
                raise BookingError("SLOT_NO_LONGER_AVAILABLE", "Khung giờ không thuộc lịch đặt này.")
            if parse_utc(slot["start_at"]) <= parse_utc(self.now()):
                raise BookingError("SLOT_NO_LONGER_AVAILABLE", "Slot đã bắt đầu hoặc đã qua.")
            if not slot["vehicle_active"] or slot["operational_status"] != "available":
                raise BookingError("VEHICLE_NOT_READY", "Xe demo không còn sẵn sàng.", retryable=True)
            if slot["battery_soc"] is None or slot["battery_soc"] < slot["minimum_booking_soc"]:
                raise BookingError("VEHICLE_NOT_READY", "Pin xe demo không còn đạt ngưỡng phục vụ.", retryable=True)
            assignment = c.execute(
                "SELECT a.sales_staff_id,s.full_name,s.phone FROM slot_sales_assignments a "
                "JOIN sales_staff s ON s.id=a.sales_staff_id AND s.status='active' AND s.is_active=1 "
                "WHERE a.slot_id=? AND a.status='assigned' AND s.status='active' ORDER BY a.created_at LIMIT 1",
                (draft["slot_id"],),
            ).fetchone()
            code = "VF" + self.now().strftime("%y%m%d") + secrets.token_hex(3).upper()
            now = iso(self.now())
            c.execute(
                "UPDATE bookings SET status='confirmed',booking_code=?,confirmed_at=?,assigned_sales_staff_id=?,version=version+1,updated_at=? WHERE id=?",
                (code, now, assignment["sales_staff_id"] if assignment else None, now, booking_id),
            )
            c.execute(
                "UPDATE test_drive_slots SET status='booked',held_until=NULL,updated_at=? WHERE id=?",
                (now, draft["slot_id"]),
            )
            c.execute(
                "UPDATE booking_driver_details SET license_check_status='pending_in_person',updated_at=? WHERE booking_id=?",
                (now, booking_id),
            )
            # A linked Zalo identity is enough to opt the recipient into the
            # live confirmation channel. Other configured channels remain
            # available as their own notification jobs.
            driver_phone = (draft.get("driver") or {}).get("phone")
            if driver_phone and hasattr(self.messaging_provider, "zalo_provider"):
                zalo_provider = self.messaging_provider.zalo_provider
                if zalo_provider and hasattr(zalo_provider, "is_linked") and zalo_provider.is_linked(driver_phone):
                    c.execute(
                        "UPDATE notification_plans SET zalo_enabled=1,updated_at=? WHERE booking_id=?",
                        (now, booking_id),
                    )
            self._create_jobs(c, booking_id, slot["start_at"])
            self._create_internal_booking_notifications(
                c,
                booking_id=booking_id,
                booking_code=code,
                showroom_id=slot["showroom_id"],
                sales_staff_id=assignment["sales_staff_id"] if assignment else None,
                start_at=slot["start_at"],
            )
            self._event(c, booking_id, "booking_confirmed", "user")
            result = {
                "booking_id": booking_id,
                "booking_code": code,
                "status": "confirmed",
                "confirmed_at": now,
                "advisor": (
                    {
                        "id": assignment["sales_staff_id"],
                        "full_name": assignment["full_name"],
                        "phone": assignment["phone"],
                    }
                    if assignment
                    else None
                ),
            }
            self._save_idempotency(c, ui_action_id, "confirm_booking", request_payload, result, now)
            return result

    def _create_internal_booking_notifications(
        self,
        c,
        *,
        booking_id: str,
        booking_code: str,
        showroom_id: str,
        sales_staff_id: str | None,
        start_at: str,
    ) -> None:
        recipients = []
        if sales_staff_id:
            staff_user = c.execute(
                "SELECT id FROM internal_users WHERE staff_id=? AND role='staff' AND is_active=1",
                (sales_staff_id,),
            ).fetchone()
            if staff_user:
                recipients.append(staff_user["id"])
        manager_rows = c.execute(
            "SELECT u.id FROM internal_users u JOIN internal_user_showrooms scope ON scope.user_id=u.id "
            "WHERE scope.showroom_id=? AND u.role='showroom_manager' AND u.is_active=1",
            (showroom_id,),
        ).fetchall()
        recipients.extend(row["id"] for row in manager_rows)
        if not recipients:
            return

        showroom = c.execute("SELECT name FROM showrooms WHERE id=?", (showroom_id,)).fetchone()
        start = parse_utc(start_at).astimezone(VIETNAM_TZ)
        title = f"Booking mới {booking_code}"
        body = (
            f"{showroom['name']} có lịch lái thử lúc {start.strftime('%H:%M ngày %d/%m/%Y')}."
            if showroom
            else f"Có lịch lái thử lúc {start.strftime('%H:%M ngày %d/%m/%Y')}."
        )
        now = iso(self.now())
        for recipient_user_id in dict.fromkeys(recipients):
            c.execute(
                "INSERT INTO internal_notifications("
                "id,recipient_user_id,booking_id,showroom_id,notification_type,title,body,read_at,created_at"
                ") VALUES(?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(recipient_user_id,booking_id,notification_type) DO NOTHING",
                (
                    _id("inotif"),
                    recipient_user_id,
                    booking_id,
                    showroom_id,
                    "booking_confirmed",
                    title,
                    body,
                    None,
                    now,
                ),
            )

    def _create_jobs(self, c, bid, start, *, confirmation_type: str = "booking_confirmation"):
        start_dt = parse_utc(start)
        now = iso(self.now())
        recipient_channels, plan = self._notification_recipient_channels(c, bid)
        schedule = [(confirmation_type, self.now())]
        for offset in self._reminder_offsets_minutes(plan):
            scheduled_at = start_dt - timedelta(minutes=offset)
            if scheduled_at > parse_utc(self.now()):
                typ = "reminder_24h" if offset == 1440 else "reminder_2h" if offset == 120 else "reminder"
                schedule.append((typ, scheduled_at))
        for recipient, channels in recipient_channels:
            for typ, when in schedule:
                for channel in channels:
                    c.execute(
                        "INSERT INTO notification_jobs(id,booking_id,recipient_person_id,notification_type,channel,scheduled_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                        (_id("job"), bid, recipient, typ, channel, iso(when), now, now),
                    )

    def _create_transactional_notification_jobs(self, c, bid: str, notification_type: str) -> None:
        now = iso(self.now())
        recipient_channels, _ = self._notification_recipient_channels(c, bid)
        for recipient, channels in recipient_channels:
            for channel in channels:
                c.execute(
                    "INSERT INTO notification_jobs(id,booking_id,recipient_person_id,notification_type,channel,scheduled_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                    (_id("job"), bid, recipient, notification_type, channel, now, now, now),
                )

    def _notification_recipient_channels(self, c, bid: str):
        booking = c.execute("SELECT booker_person_id,driver_person_id FROM bookings WHERE id=?", (bid,)).fetchone()
        plan = c.execute("SELECT * FROM notification_plans WHERE booking_id=?", (bid,)).fetchone()
        recipients = [booking["driver_person_id"]]
        if (plan["copy_booker"] or booking["booker_person_id"] != booking["driver_person_id"]) and booking["booker_person_id"] not in recipients:
            recipients.append(booking["booker_person_id"])
        result = []
        for recipient in recipients:
            person = c.execute("SELECT * FROM people WHERE id=?", (recipient,)).fetchone()
            channels = []
            if plan["zalo_enabled"] and person["phone"]:
                channels.append("zalo")
            if plan["sms_enabled"] and person["phone"]:
                channels.append("sms")
            if plan["email_enabled"] and person["email"]:
                channels.append("email")
            if not channels:
                channels = ["email" if person["email"] else "sms"]
            result.append((recipient, channels))
        return result, plan

    @staticmethod
    def _reminder_offsets_minutes(plan) -> list[int]:
        offsets: list[int] = []
        try:
            custom = json.loads(plan["custom_plan_json"] or "{}")
        except (TypeError, ValueError):
            custom = {}
        custom_offsets = custom.get("reminder_offsets_minutes") if isinstance(custom, dict) else None
        if isinstance(custom_offsets, list):
            for value in custom_offsets:
                try:
                    minutes = int(value)
                except (TypeError, ValueError):
                    continue
                if 0 < minutes <= 30 * 24 * 60:
                    offsets.append(minutes)
        else:
            if plan["reminder_24h_enabled"]:
                offsets.append(1440)
            if plan["reminder_2h_enabled"]:
                offsets.append(120)
        return sorted(set(offsets), reverse=True)[:5]

    def expire_held_bookings(self) -> int:
        count = 0
        with self.db.transaction(immediate=True) as c:
            lock = " FOR UPDATE SKIP LOCKED" if c.dialect == "postgres" else ""
            for b in c.execute(
                "SELECT * FROM bookings WHERE status='held' AND hold_expires_at<=?" + lock, (iso(self.now()),)
            ).fetchall():
                self._expire_hold_in_transaction(c, b)
                count += 1
        return count
