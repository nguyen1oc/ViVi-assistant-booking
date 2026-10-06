"""Gửi thử toàn bộ thư mẫu tới một địa chỉ, để duyệt giao diện trên máy thật.

    python backend/scripts/send_email_previews.py nguoinhan@example.com

Chạy TAY. Script này GỬI THƯ THẬT nên bắt buộc phải truyền địa chỉ nhận, không
có giá trị mặc định.

Vì sao cần: mở file trong resources/mockups/ bằng trình duyệt chỉ cho biết bố cục.
Những thứ chỉ lộ ra trên máy thật thì trình duyệt không nói được:
  - ứng dụng mail có đảo màu theo chế độ sáng/tối của máy không
  - ảnh cid: có hiện không, ảnh nền cid: có được đọc không
  - chữ có rơi về font hệ thống đúng như tính không

Cần đặt hai biến môi trường trước khi chạy:
  MEDIA_BASE_URL  URL tuyệt đối của kho ảnh. Để trống hoặc để đường dẫn tương
                  đối thì thư bỏ hẳn phần ảnh xe.
  GMAIL_*         khoá gửi thư, xem require_production_otp_secret trong config.

Dữ liệu dùng để dựng thư lấy từ một lịch hẹn CÓ THẬT trong cơ sở dữ liệu, chỉ
thay tên và email người nhận. Nhờ vậy thư gửi ra giống hệt thư khách sẽ nhận.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "backend"))

from src.config import get_settings  # noqa: E402
from src.services.booking.email_templates import (  # noqa: E402
    render_booking_dark_email,
    render_otp_email,
)
from src.services.booking.gmail_provider import GmailMessagingProvider  # noqa: E402

SQL = (
    "SELECT b.booking_code,booker.full_name booker_name,driver.full_name driver_name,"
    "driver.phone driver_phone,driver.email driver_email,m.name model_name,m.code model_code,"
    "v.name variant_name,v.estimated_range_km,v.motor_power_kw,v.battery_capacity_kwh,"
    "m.seat_count,s.name showroom_name,s.address showroom_address,"
    "s.latitude showroom_lat,s.longitude showroom_lng,t.start_at,"
    "staff.full_name staff_name,staff.phone staff_phone "
    "FROM bookings b JOIN test_drive_slots t ON t.id=b.slot_id JOIN showrooms s ON s.id=t.showroom_id "
    "JOIN demo_vehicles d ON d.id=t.demo_vehicle_id JOIN vehicle_variants v ON v.id=d.variant_id "
    "JOIN vehicle_models m ON m.id=v.model_id "
    "LEFT JOIN people booker ON booker.id=b.booker_person_id "
    "LEFT JOIN people driver ON driver.id=b.driver_person_id "
    "LEFT JOIN sales_staff staff ON staff.id=b.assigned_sales_staff_id "
    "WHERE b.status='confirmed' LIMIT 1"
)

# Mỗi loại một thư là đủ. Ba mốc nhắc lịch dùng chung một bản chữ nên chỉ gửi một.
KINDS = ("booking_confirmation", "reminder", "reschedule_confirmation",
         "booking_update", "cancellation_confirmation")


def _row(recipient: str) -> dict:
    connection = sqlite3.connect(_REPO / "backend" / "data" / "app.db")
    connection.row_factory = sqlite3.Row
    found = connection.execute(SQL).fetchone()
    if found is None:
        sys.exit("Không có lịch hẹn nào ở trạng thái confirmed trong data/app.db")
    row = dict(found)
    row["driver_email"] = recipient
    # Lịch đổi giờ trỏ ngược về lịch cũ. Lịch mẫu không có nên đặt tay một giờ cũ,
    # nếu không thư đổi giờ sẽ thiếu hàng đối chiếu và duyệt không ra vấn đề gì.
    row.setdefault("previous_start_at", None)
    if not row["previous_start_at"]:
        row["previous_start_at"] = "2026-08-19T07:30:00Z"
    return row


def main() -> int:
    if len(sys.argv) < 2 or "@" not in sys.argv[1]:
        sys.exit("Thiếu địa chỉ nhận. Ví dụ: python backend/scripts/send_email_previews.py ban@example.com")
    recipient = sys.argv[1]

    settings = get_settings()
    if not settings.gmail_enabled:
        sys.exit("GMAIL_ENABLED đang tắt.")
    if not settings.media_base_url.startswith(("http://", "https://")):
        print(f"CẢNH BÁO: MEDIA_BASE_URL='{settings.media_base_url}' không phải URL tuyệt đối.")
        print("         Thư gửi ra sẽ KHÔNG có ảnh xe. Đặt lại rồi chạy lại nếu muốn xem ảnh.")

    provider = GmailMessagingProvider(
        client_id=settings.gmail_client_id,
        client_secret=settings.gmail_client_secret,
        refresh_token=settings.gmail_refresh_token,
        sender_email=settings.gmail_sender_email,
        sender_name=settings.gmail_sender_name,
        timeout_seconds=settings.gmail_timeout_seconds,
    )
    row = _row(recipient)

    letters = [(kind, render_booking_dark_email(kind, row)) for kind in KINDS]
    letters.append(("otp", render_otp_email(code="482913", expires_in_seconds=300)))

    sent = failed = 0
    for kind, mail in letters:
        result = provider.send_message(
            channel="email",
            destination=recipient,
            subject=mail.subject,
            body=mail.plain_text,
            html_body=mail.html,
            inline_images=mail.inline_images,
        )
        ok = result.provider_status == "sent"
        sent, failed = sent + ok, failed + (not ok)
        detail = result.provider_message_id if ok else (result.sanitized_response or {}).get("error")
        print(f"  {'OK   ' if ok else 'HỎNG '} {kind:26} {detail}")

    print(f"Gửi được {sent}, hỏng {failed}. Người nhận: {recipient}")
    if failed:
        print("Nếu lỗi là oauth_error_400 thì GMAIL_REFRESH_TOKEN đã hết hiệu lực, phải lấy khoá mới.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
