"""Sinh bản xem trước của TẤT CẢ thư nền tối ra resources/mockups/.

Chạy TAY mỗi khi sửa giao diện thư:

    python backend/scripts/preview_confirmation_email.py

Sinh bản mẫu và bản xem trước cho SÁU loại thư:

    email-xac-nhan     xác nhận lịch hẹn
    email-nhac-lich    nhắc lịch
    email-doi-gio      đổi giờ
    email-cap-nhat     cập nhật lịch
    email-huy-lich     huỷ lịch
    email-ma-xac-thuc  mã xác thực

Mỗi loại ra hai file: `<tên>.html` còn nguyên {{biến}} để đối chiếu danh sách
trường, và `<tên>.preview.html` đã điền dữ liệu giả để xem mặt mũi.

VÌ SAO SINH RA CHỨ KHÔNG VIẾT TAY: trước đây bản mockup là một file HTML riêng,
chép tay song song với email_templates.py. Sửa một bên quên bên kia là hai bản
lệch nhau, và đã lệch thật vài lần. Nay bản mẫu ĐƯỢC SINH TỪ CHÍNH bộ render của
backend nên không thể lệch. Đừng sửa tay hai file trong resources/mockups/, sửa
email_templates.py rồi chạy lại lệnh này.

Ảnh inline trong thư đi bằng cid:, mà trình duyệt không hiểu cid:. Ở đây đổi sang
data: URI để mở bằng trình duyệt là xem được ngay. Thư gửi thật vẫn dùng cid:.
"""

from __future__ import annotations

import base64
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "backend"))

from src.services.booking.email_templates import (  # noqa: E402
    _ASSETS_DIR,
    _booking_facts,
    render_booking_dark_email,
    render_otp_email,
)
from src.services.booking.public_invitation import public_invitation_url  # noqa: E402

OUT_DIR = _REPO / "resources" / "mockups"
CDN = "https://pub-216eea433b9e4529979ce534d5ce0ae1.r2.dev"

# Tên biến trong bản mẫu phải trùng tên cột trong câu SELECT của _render_notification.
PLACEHOLDER = {
    "booking_code": "{{ma_lich_hen}}",
    "booker_name": "{{ho_ten_khach}}",
    "driver_name": "{{ho_ten_khach}}",
    "driver_phone": "{{sdt_khach}}",
    "driver_email": "{{email_khach}}",
    "model_name": "{{ten_model_xe}}",
    "model_code": "VF8",
    "variant_name": "{{phien_ban}}",
    # Thông số cũng là ô điền. Trước đây để số thật ở đây, nhìn vào bản mẫu tưởng
    # thông số bị đặt cứng trong mã, trong khi bộ render vẫn đọc từ cơ sở dữ liệu.
    "estimated_range_km": "{{quang_duong_km}}",
    "motor_power_kw": "{{cong_suat_kw}}",
    "battery_capacity_kwh": "{{pin_kwh}}",
    "seat_count": "{{so_cho}}",
    "showroom_name": "{{ten_showroom}}",
    "showroom_address": "{{dia_chi_showroom}}",
    "showroom_lat": None,
    "showroom_lng": None,
    "start_at": "2026-08-21T02:00:00Z",
    # Chỉ thư đổi giờ dùng tới. Có giá trị thì card hiện thêm hàng "Giờ trước đây"
    # gạch ngang để đối chiếu; rỗng thì bỏ hàng đó đi.
    "previous_start_at": "2026-08-19T07:30:00Z",
    "staff_name": "{{ten_nv}}",
    "staff_phone": "{{sdt_nv}}",
}

SAMPLE = {
    **PLACEHOLDER,
    "booking_code": "VF260821A47C3D",
    "booker_name": "Nguyễn Hoàng Minh",
    "driver_name": "Nguyễn Hoàng Minh",
    "driver_phone": "0901 234 567",
    "driver_email": "minh.nguyen@example.com",
    "model_name": "VF 8",
    "variant_name": "Plus",
    # Số thật của VinFast VF 8 bản Plus, lấy đúng từ data/app.db. Đừng bịa số ở
    # đây: bản xem trước mà sai số thì người duyệt tưởng thư gửi ra cũng sai.
    "estimated_range_km": 447.0,
    "motor_power_kw": 300.0,
    "battery_capacity_kwh": 87.7,
    "seat_count": 5,
    "showroom_name": "VinFast Tân Phong",
    "showroom_address": "1058 Nguyễn Văn Linh, phường Tân Phong, TP.HCM",
    "showroom_lat": 10.7295,
    "showroom_lng": 106.7183,
    "staff_name": "Trần Thu Hà",
    "staff_phone": "0912 888 456",
}


def _data_uri(name: str) -> str:
    return "data:image/png;base64," + base64.b64encode((_ASSETS_DIR / name).read_bytes()).decode()


def _mask_dates(html: str) -> str:
    """Đổi giờ hẹn đã dựng thành ô điền, chỉ dùng cho BẢN MẪU.

    Giờ hẹn không truyền thẳng chuỗi {{...}} vào được: bộ render phải phân tích
    ngày giờ thật để biết thứ mấy và lấy năm cho dòng bản quyền. Nên ở đây dựng
    bằng ngày thật rồi thay ngược lại thành ô điền.

    Lấy chuỗi từ chính _booking_facts() chứ không gõ tay, để bản mẫu không lệch
    khi ai đó đổi cách viết ngày giờ trong email_templates.py.
    """
    facts = _booking_facts(PLACEHOLDER)
    for value, token in (
        (facts["when"], "{{thoi_gian_hen}}"),
        (facts["when_prose"], "{{thoi_gian_hen}}"),
        (facts["previous_when"], "{{gio_truoc_day}}"),
    ):
        if value:
            html = html.replace(value, token)
    return html


def _browser_ready(html: str) -> str:
    """Đổi cid: sang data: để mở bằng trình duyệt xem được."""
    for cid, name in (
        ("vinfast-logo-band-small", "email-logo-band-small.png"),
        ("vinfast-logo-band", "email-logo-band.png"),
        ("vinfast-bg-base", "email-bg-base.png"),
        ("vinfast-bg-card", "email-bg-card.png"),
    ):
        html = html.replace(f"cid:{cid}", _data_uri(name))
    return html


HEADER_NOTE = """<!--
  ═══════════════════════════════════════════════════════════════════════════════
  BẢN NÀY ĐƯỢC SINH RA, ĐỪNG SỬA TAY
  ═══════════════════════════════════════════════════════════════════════════════
  Sinh bằng: python backend/scripts/preview_confirmation_email.py
  Nguồn thật: backend/src/services/booking/email_templates.py
              -> render_booking_confirmation_email()

  Sửa giao diện thư thì sửa file nguồn rồi chạy lại lệnh trên. Sửa tay ở đây là
  bản mẫu và thư gửi thật lệch nhau, đã xảy ra vài lần trước khi có script này.

  Ảnh inline ở đây là data: URI cho trình duyệt mở được. Thư gửi thật dùng cid:
  và đính kèm ảnh vào thư.
-->
"""


def main() -> int:
    import os

    os.environ.setdefault("MEDIA_BASE_URL", CDN)
    # Bản HTML xem trước phải mở thiệp MẪU của frontend hiện tại. Không dùng
    # token production giả ở đây: token được ký bằng secret của máy sinh file,
    # nên khi bấm sang một deployment khác nó không còn hợp lệ và dễ khiến người
    # duyệt tưởng CTA đang trỏ nhầm về trang chủ. Email gửi thật không đi qua
    # nhánh này và vẫn giữ URL /invitation/{token} cá nhân hoá.
    invitation_preview_url = os.environ.get(
        "INVITATION_PREVIEW_URL",
        "http://localhost:3000/invitation-preview",
    ).strip()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Mỗi loại thư ra HAI file: bản mẫu còn nguyên {{biến}} để đối chiếu danh sách
    # trường, và bản đã điền dữ liệu giả để xem mặt mũi.
    jobs: tuple[tuple[str, str], ...] = (
        ("email-xac-nhan", "booking_confirmation"),
        ("email-nhac-lich", "reminder"),
        ("email-doi-gio", "reschedule_confirmation"),
        ("email-cap-nhat", "booking_update"),
        ("email-huy-lich", "cancellation_confirmation"),
    )
    for stem, kind in jobs:
        for suffix, data in ((".html", PLACEHOLDER), (".preview.html", SAMPLE)):
            html = _browser_ready(render_booking_dark_email(kind, data).html)
            if data is PLACEHOLDER:
                html = _mask_dates(html)
            elif kind in {
                "booking_confirmation",
                "reschedule_confirmation",
                "reminder",
                "booking_update",
            }:
                signed_url = public_invitation_url(str(data["booking_code"]))
                html = html.replace(
                    f'href="{signed_url}"',
                    f'href="{invitation_preview_url}"',
                )
            target = OUT_DIR / f"{stem}{suffix}"
            target.write_text(HEADER_NOTE + html)
            print(f"  {target.relative_to(_REPO)}  {target.stat().st_size // 1024} KB")

    # Thư mã xác thực nhận tham số rời chứ không nhận cả một hàng dữ liệu, nên
    # bản mẫu phải thay chữ sau khi dựng. `expires_in_seconds` là số, truyền chuỗi
    # {{...}} vào là vỡ phép chia, nên dựng với 300 giây rồi đổi "5 phút" thành ô điền.
    for suffix, code, minutes in ((".html", "{{ma_xac_thuc}}", "{{hieu_luc_phut}}"), (".preview.html", "482913", "5")):
        html = _browser_ready(render_otp_email(code=code, expires_in_seconds=300).html)
        if minutes != "5":
            html = html.replace("5 phút", f"{minutes} phút")
        target = OUT_DIR / f"email-ma-xac-thuc{suffix}"
        target.write_text(HEADER_NOTE + html)
        print(f"  {target.relative_to(_REPO)}  {target.stat().st_size // 1024} KB")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
