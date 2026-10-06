from __future__ import annotations

import json
import logging
from datetime import timedelta
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from src.services.booking.base import BookingBase
from src.services.booking.common import iso
from src.services.booking.email_templates import render_booking_email

if TYPE_CHECKING:
    from src.services.profile.driver_invitation import DriverInvitationService

VIETNAM_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


class BackgroundJobService(BookingBase):
    # Wired by src.dependencies after DriverInvitationService is constructed.
    # Keeping the attribute explicit avoids silently losing the driver link when
    # this mixin is used by a BookingService instance.
    driver_invitation_service: DriverInvitationService | None = None

    def dispatch_due_notifications(self, batch_size: int = 100, processing_timeout_seconds: int = 300) -> dict:
        stale_before = iso(self.now() - timedelta(seconds=processing_timeout_seconds))
        with self.db.transaction(immediate=True) as c:
            c.execute(
                "UPDATE notification_jobs SET status='pending',updated_at=?,error_message=? "
                "WHERE status='processing' AND last_attempt_at<=? AND attempt_count<max_attempts",
                (iso(self.now()), "processing_timeout_recovered", stale_before),
            )
            c.execute(
                "UPDATE notification_jobs SET status='failed',updated_at=?,error_message=? "
                "WHERE status='processing' AND last_attempt_at<=? AND attempt_count>=max_attempts",
                (iso(self.now()), "processing_timeout_terminal", stale_before),
            )
            rows = c.execute(
                "SELECT j.*,p.phone,p.email,p.preferred_channel FROM notification_jobs j "
                "JOIN people p ON p.id=j.recipient_person_id WHERE j.status='pending' AND j.scheduled_at<=? "
                "ORDER BY j.scheduled_at LIMIT ?",
                (iso(self.now()), batch_size),
            ).fetchall()
            ids = [row["id"] for row in rows]
            for job_id in ids:
                c.execute(
                    "UPDATE notification_jobs SET status='processing',attempt_count=attempt_count+1,last_attempt_at=?,updated_at=? WHERE id=? AND status='pending'",
                    (iso(self.now()), iso(self.now()), job_id),
                )
        sent = failed = 0
        for row in rows:
            destination = row["email"] if row["channel"] == "email" else row["phone"]
            try:
                rendered = self._render_notification(
                    row["booking_id"], row["notification_type"], row["recipient_person_id"]
                )
                result = (
                    self.messaging_provider.send_message(
                        channel=row["channel"],
                        destination=destination,
                        subject=rendered.subject,
                        # SMS và Zalo lấy bản rút gọn. `plain_text` là nhánh
                        # text/plain của email, dài cả chục dòng, gửi vào tin
                        # nhắn là vỡ. Loại thư nào không có bản rút gọn thì rơi
                        # về plain_text như trước.
                        body=(
                            rendered.plain_text
                            if row["channel"] == "email"
                            else (rendered.sms_text or rendered.plain_text)
                        ),
                        html_body=rendered.html,
                        # THIẾU dòng này là logo đầu thư vỡ: thân HTML trỏ `cid:vinfast-logo`
                        # nhưng không có ảnh nào được đính kèm. Mail OTP đi đường khác
                        # (GmailMessagingProvider.send) nên vẫn hiện, mail lịch thì không.
                        inline_images=rendered.inline_images,
                    )
                    if destination
                    else None
                )
                error_message = (
                    "recipient_channel_unavailable"
                    if result is None
                    else (result.sanitized_response or {}).get("error") or result.provider_status
                )
            except Exception as error:  # provider outages must not stop the remaining jobs
                result = None
                error_message = str(error)
            with self.db.transaction(immediate=True) as c:
                if result and (result.provider_status in ("sent", "mocked") or result.is_mock):
                    c.execute(
                        "UPDATE notification_jobs SET status='sent',sent_at=?,provider_name=?,provider_status=?,provider_message_id=?,is_mock=?,provider_response_json=?,updated_at=? WHERE id=? AND status='processing'",
                        (
                            iso(self.now()),
                            result.provider,
                            result.provider_status,
                            result.provider_message_id,
                            int(result.is_mock),
                            json.dumps(result.sanitized_response or {}),
                            iso(self.now()),
                            row["id"],
                        ),
                    )
                    self._event(
                        c,
                        row["booking_id"],
                        "notification_sent",
                        "system",
                        {"job_id": row["id"], "provider_status": result.provider_status, "is_mock": result.is_mock},
                    )
                    sent += 1
                else:
                    retryable = getattr(result, "retryable", True) if result else True
                    terminal = not retryable or row["attempt_count"] + 1 >= row["max_attempts"]
                    c.execute(
                        "UPDATE notification_jobs SET status=?,provider_name=?,provider_status=?,is_mock=?,provider_response_json=?,error_message=?,updated_at=? WHERE id=? AND status='processing'",
                        (
                            "failed" if terminal else "pending",
                            getattr(result, "provider", None),
                            getattr(result, "provider_status", None),
                            int(getattr(result, "is_mock", True)),
                            json.dumps(getattr(result, "sanitized_response", None) or {}),
                            error_message,
                            iso(self.now()),
                            row["id"],
                        ),
                    )
                    failed += 1
        return {"claimed": len(rows), "sent": sent, "failed": failed, "is_mock": True}

    def _render_notification(self, booking_id: str, notification_type: str, recipient_person_id: str | None = None):
        with self.db.connect() as c:
            row = c.execute(
                # Gộp cột của hai nhánh: booker_person_id và driver_person_id phục vụ
                # link mời người lái, phần còn lại phục vụ thư nền tối.
                "SELECT b.booking_code,b.booker_person_id,b.driver_person_id,"
                "booker.full_name booker_name,booker.phone booker_phone,booker.email booker_email,"
                "driver.full_name driver_name,driver.phone driver_phone,driver.email driver_email,"
                "m.name model_name,m.code model_code,"
                "v.name variant_name,v.estimated_range_km,v.motor_power_kw,v.battery_capacity_kwh,"
                "m.seat_count,s.name showroom_name,s.address showroom_address,"
                "s.latitude showroom_lat,s.longitude showroom_lng,"
                "t.start_at,prevslot.start_at previous_start_at,"
                "staff.full_name staff_name,staff.phone staff_phone "
                "FROM bookings b JOIN test_drive_slots t ON t.id=b.slot_id JOIN showrooms s ON s.id=t.showroom_id "
                "JOIN demo_vehicles d ON d.id=t.demo_vehicle_id JOIN vehicle_variants v ON v.id=d.variant_id "
                "JOIN vehicle_models m ON m.id=v.model_id "
                "LEFT JOIN people booker ON booker.id=b.booker_person_id "
                "LEFT JOIN people driver ON driver.id=b.driver_person_id "
                "LEFT JOIN sales_staff staff ON staff.id=b.assigned_sales_staff_id "
                # Lịch đổi giờ trỏ ngược về lịch cũ, lấy theo để thư đổi giờ nói
                # được "từ giờ nào sang giờ nào" thay vì chỉ đưa ra giờ mới.
                "LEFT JOIN bookings prev ON prev.id=b.rescheduled_from_booking_id "
                "LEFT JOIN test_drive_slots prevslot ON prevslot.id=prev.slot_id WHERE b.id=?",
                (booking_id,),
            ).fetchone()
        if not row:
            return render_booking_email(
                notification_type, row, driver_invite_url=None, recipient_person_id=recipient_person_id
            )
        driver_invite_url = None
        invitation_service = getattr(self, "driver_invitation_service", None)
        if (
            notification_type == "booking_confirmation"
            and invitation_service is not None
            and recipient_person_id
            and str(recipient_person_id) == str(row["driver_person_id"])
            and row["driver_person_id"] != row["booker_person_id"]
        ):
            try:
                driver_invite_url = invitation_service.issue(booking_id).url
            except Exception:
                logging.getLogger(__name__).exception(
                    "Failed to issue driver invitation link for booking %s", booking_id
                )
                driver_invite_url = None
        return render_booking_email(
            notification_type,
            row,
            driver_invite_url=driver_invite_url,
            recipient_person_id=recipient_person_id,
        )
