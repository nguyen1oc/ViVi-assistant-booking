"""Mẫu email gửi cho khách: mã OTP và các thông báo về lịch lái thử.

Viết lại 18/08/2026 theo phản hồi của chủ dự án. Hai việc được sửa:

1. TOÀN BỘ CHỮ NAY CÓ DẤU. Bản trước viết tiếng Việt không dấu ("Ma OTP xac thuc lich lai
   thu") — đọc khó và trông như thư rác, nhất là khi đây là email xác nhận đầu tiên khách
   nhận từ VinFast. `EmailMessage.set_content()` / `add_alternative()` của Python tự chọn
   UTF-8 khi gặp ký tự ngoài ASCII, còn dòng Subject được tự mã hoá theo RFC 2047, nên
   không cần đổi gì ở `gmail_provider.py`.

2. BỐ CỤC HTML DỰNG LẠI. Bản trước chỉ có `<h2>`, `<p>` và một `<table>` trần: không khai
   báo charset, không giới hạn bề ngang nên trên màn rộng chữ chạy dài sát mép trái, cỡ chữ
   thả theo mặc định của từng ứng dụng mail nên mỗi nơi một kiểu.

   Nguyên tắc khi sửa file này: email KHÔNG dùng flex/grid/`<style>` ngoài — Outlook và một
   số webmail bỏ qua hoặc hiểu sai. Chỉ dùng bảng lồng bảng và style nội tuyến; đó là lý do
   mã dưới đây trông cổ hơn HTML thường.

3. RÚT NGẮN CHIỀU CAO (18/08/2026). Bản trước mỗi dòng xếp nhãn trên - giá trị dưới, 9 dòng
   liền nhau nên thư cao hơn 900px, mở trên Gmail phải cuộn mới xem hết. Nay mỗi dòng gói
   trong MỘT hàng: nhãn xám bên trái, giá trị đậm bên phải (kiểu hoá đơn), và gộp điện thoại
   với email thành một dòng "Liên hệ". Chiều cao còn khoảng một nửa, vừa trọn một màn.

4. LOGO THAY CHO CHỮ. Đầu thư trước đây là chữ "VINFAST" màu xanh dựng bằng CSS. Nay dùng
   ảnh logo thật, nhúng theo kiểu CID (`cid:vinfast-logo`) chứ không phải `data:` URI —
   Gmail chặn ảnh `data:`. File ảnh nằm cạnh file này ở `assets/vinfast-logo.png` và được
   `RenderedEmail.inline_images` trả về cho tầng gửi thư đính kèm.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from html import escape
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

from src.config import get_settings
from src.services.booking.common import parse_utc
from src.services.booking.public_invitation import public_invitation_url

VIETNAM_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
WEEKDAYS_VI = ("Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật")

# Màu và font lấy đúng theo giao diện web để email không lạc khỏi thương hiệu.
_INK = "#171a20"
_MUTED = "#6b7280"
_BLUE = "#1464f4"
_PAPER = "#f4f4f4"
_LINE = "#e5e7eb"
_FONT = (
    "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif"
)

_LOGO_PATH = Path(__file__).with_name("assets") / "vinfast-logo.png"
_LOGO_CID = "vinfast-logo"


@lru_cache(maxsize=1)
def _logo_bytes() -> bytes:
    """Đọc một lần rồi giữ trong bộ nhớ — mỗi email đều cần đúng file này."""
    try:
        return _LOGO_PATH.read_bytes()
    except OSError:
        return b""


@dataclass(frozen=True)
class InlineImage:
    """Ảnh nhúng trong thân thư, tham chiếu bằng `cid:<cid>`."""

    cid: str
    content: bytes
    subtype: str = "png"


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    plain_text: str
    html: str
    # Bản rút gọn cho SMS và Zalo. Rỗng thì tầng gửi dùng `plain_text`.
    # Cần trường riêng vì `plain_text` là nhánh text/plain của email, dài cả chục
    # dòng; nhét nguyên vào một tin nhắn là vừa tốn tiền vừa không ai đọc.
    sms_text: str = ""
    # Tầng gửi thư đính kèm những ảnh này dưới dạng inline; rỗng thì thân thư vẫn đọc được
    # bình thường, chỉ mất logo và hiện chữ thay thế "VinFast".
    inline_images: tuple[InlineImage, ...] = field(default_factory=tuple)


def _inline_logo() -> tuple[InlineImage, ...]:
    data = _logo_bytes()
    return (InlineImage(cid=_LOGO_CID, content=data),) if data else ()


def render_booking_email(
    notification_type: str,
    row,
    *,
    driver_invite_url: str | None = None,
    recipient_person_id: str | None = None,
) -> RenderedEmail:
    """Điểm vào duy nhất cho mọi thư về lịch hẹn.

    `driver_invite_url` chỉ có giá trị khi người đặt KHÁC người lái: đó là link
    mời người lái vào trò chuyện với ViVi. Thư nền tối thay đích/nội dung CTA
    chính bằng link này, xem render_booking_dark_email().
    """
    # Mọi loại thư về lịch hẹn đều đi bản nền tối nhấn vàng, chung một bộ khung.
    # Chỉ khi thiếu dữ liệu lịch mới rơi về bản nền sáng tối giản bên dưới, vì lúc
    # đó không cá nhân hoá được gì.
    if row and notification_type in _BOOKING_COPY:
        return render_booking_dark_email(
            notification_type,
            row,
            driver_invite_url=driver_invite_url,
            recipient_person_id=recipient_person_id,
        )
    if not row:
        subject = "Cập nhật lịch lái thử VinFast"
        plain = "Lịch lái thử VinFast của bạn đã được cập nhật."
        return RenderedEmail(
            subject=subject,
            plain_text=plain,
            html=_html_document(title=subject, intro=plain, rows=()),
            inline_images=_inline_logo(),
        )

    start = parse_utc(row["start_at"]).astimezone(VIETNAM_TZ)
    heading = _heading(notification_type)
    subject = f"{heading} - {row['booking_code'] or 'VinFast'}"
    staff = row["staff_name"] or "VinFast sẽ liên hệ"
    if row["staff_phone"]:
        staff = f"{staff} - {row['staff_phone']}"
    booker = row["booker_name"] or "-"
    driver = row["driver_name"] or "-"
    contact = " · ".join(v for v in (row["driver_phone"], row["driver_email"]) if v) or "-"
    people = (
        # Đặt hộ mới cần tách hai dòng; đa số trường hợp người đặt cũng là người lái.
        (("Người đặt lịch", booker), ("Người lái thử", driver))
        if driver != booker
        else ((("Người đặt & lái thử"), booker),)
    )
    # Nút chỉ đường Google Maps — tính năng đến từ nhánh testing (PR #55), giữ nguyên khi gộp.
    showroom_name = row["showroom_name"] or "Showroom VinFast"
    maps_url = f"https://www.google.com/maps/search/?api=1&query={quote(showroom_name)}"
    rows = (
        ("Mã lịch", row["booking_code"] or "-"),
        (
            "Thời gian",
            f"{start.strftime('%H:%M')} - {WEEKDAYS_VI[start.weekday()]}, {start.strftime('%d/%m/%Y')}",
        ),
        ("Mẫu xe", f"{row['model_name']} {row['variant_name']}"),
        ("Showroom", showroom_name),
        *people,
        ("Liên hệ", contact),
        ("Tư vấn viên", staff),
    )
    plain = "\n".join((heading, *(f"{label}: {value}" for label, value in rows)))
    invite_html = ""
    if driver_invite_url and notification_type == "booking_confirmation":
        safe_invite_url = escape(driver_invite_url, quote=True)
        invite_html = (
            '<div style="margin:22px 0 0;text-align:center;">'
            f'<a href="{safe_invite_url}" target="_blank" rel="noreferrer" '
            f'style="display:inline-block;padding:12px 24px;border-radius:10px;'
            f'background:{_BLUE};color:#ffffff;font-size:14px;font-weight:600;'
            'text-decoration:none;">Trò chuyện với ViVi</a></div>'
            '<p style="margin:10px 0 0;font-size:13px;line-height:20px;color:#6b7280;">'
            'Chia sẻ nhu cầu riêng để chuẩn bị tốt hơn cho buổi lái thử.</p>'
        )
        plain += (
            "\n\nTrò chuyện với ViVi để chuẩn bị cho buổi lái thử: "
            f"{driver_invite_url}"
        )
    html = _html_document(
        title=heading,
        intro=_intro(notification_type),
        rows=rows,
        footer=(
            "Cần đổi giờ hoặc huỷ lịch, bạn tra cứu bằng email đã đăng ký trên website VinFast."
        ),
        maps_url=maps_url,
        showroom_name=showroom_name,
        post_content_html=invite_html,
    )
    return RenderedEmail(subject=subject, plain_text=plain, html=html, inline_images=_inline_logo())


def _heading(notification_type: str) -> str:
    return {
        "booking_confirmation": "Lịch lái thử đã xác nhận",
        "booking_update": "Thông tin lịch lái thử đã cập nhật",
        "reschedule_confirmation": "Lịch lái thử đã đổi giờ",
        "cancellation_confirmation": "Lịch lái thử đã huỷ",
        "reminder": "Nhắc lịch lái thử VinFast",
        "reminder_24h": "Nhắc lịch lái thử VinFast",
        "reminder_2h": "Nhắc lịch lái thử VinFast",
    }.get(notification_type, "Cập nhật lịch lái thử VinFast")


def _intro(notification_type: str) -> str:
    return {
        "booking_confirmation": (
            "Cảm ơn bạn đã đặt lịch lái thử. Thông tin lịch hẹn của bạn như sau."
        ),
        "booking_update": "Thông tin lịch lái thử của bạn vừa được cập nhật.",
        "reschedule_confirmation": "Lịch lái thử của bạn đã được đổi sang thời gian mới.",
        "cancellation_confirmation": "Lịch lái thử của bạn đã được huỷ theo yêu cầu.",
        "reminder": "Đây là email nhắc lịch lái thử sắp diễn ra.",
        "reminder_24h": "Đây là email nhắc lịch lái thử sắp diễn ra.",
        "reminder_2h": "Đây là email nhắc lịch lái thử sắp diễn ra.",
    }.get(notification_type, "Lịch lái thử VinFast của bạn có cập nhật mới.")


def _row_html(label: str, value: str, *, last: bool) -> str:
    """Một dòng thông tin gói trong MỘT hàng: nhãn trái, giá trị phải.

    Bản trước xếp nhãn trên - giá trị dưới nên mỗi dòng cao ~70px, chín dòng là thư đã dài quá
    một màn. Kiểu hoá đơn này cao khoảng một nửa mà vẫn đọc được, và chạy đúng ở mọi ứng dụng
    mail vì chỉ là một `<tr>` hai `<td>`.
    """
    border = "" if last else f"border-bottom:1px solid {_LINE};"
    return (
        f'<tr>'
        f'<td style="padding:11px 12px 11px 0;{border}font-size:14px;line-height:20px;'
        f'color:{_MUTED};white-space:nowrap;vertical-align:top;">{escape(str(label))}</td>'
        f'<td align="right" style="padding:11px 0;{border}font-size:15px;line-height:20px;'
        f'color:{_INK};font-weight:600;word-break:break-word;">{escape(str(value))}</td>'
        "</tr>"
    )


def _html_document(
    *,
    title: str,
    intro: str,
    rows,
    footer: str | None = None,
    highlight: str | None = None,
    maps_url: str | None = None,
    showroom_name: str | None = None,
    post_content_html: str = "",
) -> str:
    row_list = list(rows)
    body_rows = "\n".join(
        _row_html(label, value, last=(index == len(row_list) - 1))
        for index, (label, value) in enumerate(row_list)
    )
    table_html = (
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        f'width="100%" style="width:100%;border-collapse:collapse;">{body_rows}</table>'
        if body_rows
        else ""
    )

    # Mã OTP được tách riêng thành một khối lớn: đây là thứ duy nhất người nhận cần đọc,
    # để lẫn trong bảng thì phải dò từng dòng mới thấy.
    highlight_html = (
        f'<div style="margin:0 0 24px;padding:18px 20px;background:{_PAPER};'
        f'border-radius:14px;text-align:center;">'
        f'<div style="font-size:32px;line-height:38px;font-weight:700;color:{_INK};'
        f'letter-spacing:6px;">{escape(str(highlight))}</div></div>'
        if highlight
        else ""
    )

    # Nút chỉ đường: chỉ hiện ở email về lịch hẹn (có showroom), không hiện ở email OTP.
    maps_html = (
        f'<div style="margin:18px 0 0;text-align:center;">'
        f'<a href="{escape(maps_url)}" target="_blank" rel="noreferrer" '
        f'style="display:inline-block;padding:12px 24px;border-radius:10px;'
        f'background:{_BLUE};color:#ffffff;font-size:14px;font-weight:600;'
        f'text-decoration:none;">Chỉ đường đến {escape(showroom_name or "showroom")}</a></div>'
        if maps_url
        else ""
    )

    footer_html = (
        f'<p style="margin:22px 0 0;font-size:13px;line-height:20px;color:{_MUTED};">'
        f"{escape(footer)}</p>"
        if footer
        else ""
    )

    document = f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title>
</head>
<body style="margin:0;padding:0;background:{_PAPER};">
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%"
       style="width:100%;background:{_PAPER};">
  <tr>
    <td align="center" style="padding:24px 16px;">
      <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="560"
             style="width:560px;max-width:100%;background:#ffffff;border-radius:20px;
                    border:1px solid {_LINE};">
        <tr>
          <td style="padding:24px 30px 0;font-family:{_FONT};">
            <img src="cid:{_LOGO_CID}" alt="VinFast" width="120"
                 style="display:block;width:120px;height:auto;border:0;">
          </td>
        </tr>
        <tr>
          <td style="padding:14px 30px 0;font-family:{_FONT};">
            <h1 style="margin:0;font-size:23px;line-height:29px;font-weight:650;
                       color:{_INK};letter-spacing:-0.4px;">{escape(title)}</h1>
            <p style="margin:9px 0 18px;font-size:15px;line-height:22px;color:{_MUTED};">
              {escape(intro)}</p>
          </td>
        </tr>
        <tr>
          <td style="padding:0 30px 24px;font-family:{_FONT};">
            {highlight_html}{table_html}{maps_html}{post_content_html}{footer_html}
          </td>
        </tr>
      </table>
      <div style="font-family:{_FONT};font-size:12px;line-height:18px;color:{_MUTED};
                  padding:14px 8px 0;">
        Email tự động từ hệ thống đặt lịch lái thử VinFast.
      </div>
    </td>
  </tr>
</table>
</body>
</html>"""
    return document.replace("\n    \n", "\n\n")


# ═══════════════════════════════════════════════════════════════════════════════
# PHIẾU XÁC NHẬN LỊCH HẸN — bản nền đen nhấn vàng
# ═══════════════════════════════════════════════════════════════════════════════
# Dựng theo bản duyệt ở resources/mockups/email-phieu-xac-nhan-awe.html. Sửa giao diện
# thì sửa cả hai chỗ, đừng để lệch nhau.
#
# Chỉ dùng cho notification_type = "booking_confirmation". Các loại còn lại (nhắc
# lịch, đổi giờ, huỷ) vẫn đi qua `_html_document` nền sáng ở trên vì tiêu đề
# "Phiếu xác nhận lịch hẹn" không đúng với chúng.
#
# Bộ màu, lấy đúng theo bản duyệt:
_G_BLACK = "#121212"   # Rich Black, nền chính, và là màu chữ nằm trên nền vàng
_G_CARD = "#1E1E1E"    # Charcoal Dark, nền card
# MỘT màu vàng duy nhất cho cả mảng nền lẫn chữ. Trước đây dùng hai màu và cả hai
# đều hỏng theo cách riêng:
#
#   #D4AF37  độ sáng 0.45, tương phản 7.9 trên nền card. Đổ mảng lớn thì được,
#            nhưng bóp xuống cỡ chữ 12px thì xỉn lại như màu ô liu.
#   #F3E5AB  độ sáng 0.78. Đọc rất rõ khi thư hiện đúng màu, NHƯNG sáng quá: máy
#            bật chế độ tối lật nó thành màu tối và chữ chìm hẳn.
#
#   #F5C542  độ sáng 0.60, tương phản 10.3 trên card và 11.6 với chữ đen đè lên.
#            Sáng hơn #D4AF37 thấy rõ, mà vẫn nằm giữa dải nên khi bị đảo màu nó
#            vẫn ra một màu trung tính, không chìm.
_G_GOLD = "#F5C542"
# Nút sáng hơn thanh vàng một nấc. Trước đây nút và thanh tên khách cùng một màu
# vàng, mảng vàng lớn của thanh hút hết mắt nên nút không nổi lên được. Tách hai
# sắc độ thì nút thành thứ sáng nhất thư và tự nhảy ra trước.
_G_GOLD_BTN = "#FFD24A"
_G_GOLD_EDGE = "#FFE9A8"  # mép trên nút, tạo cảm giác khối nổi
_G_MUTED_BAR = "#2A2A2A"  # thanh trung tính cho thư huỷ lịch, thay cho mảng vàng
_G_TEXT = "#E0E0E0"    # Off-White, chữ văn bản
_G_MUTED = "#8A8A8A"   # xám trung tính cho chân thư
# KHÔNG dùng webfont. Trước đây nạp Oswald và Be Vietnam Pro từ Google Fonts,
# và đó chính là chỗ hỏng font trên điện thoại: ứng dụng mail nạp được bộ ký tự
# Latin nhưng KHÔNG nạp bộ tiếng Việt, nên chữ có dấu rơi sang font khác từng ký
# tự một, ra một dòng chữ lẫn hai kiểu. Mở trong trình duyệt thì nạp đủ nên không
# thấy lỗi — đúng hiện tượng "xem trên máy tính thì ổn, xem trên điện thoại thì hỏng".
#
# Dùng font hệ thống thì chữ giống nhau ở mọi nơi. Đổi lại mất dáng chữ hẹp của
# Oswald, bù bằng chữ hoa, nét đậm và giãn chữ.
_G_HEAD = "-apple-system,'Helvetica Neue',Roboto,Helvetica,Arial,sans-serif"
_G_BODY = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Helvetica,Arial,sans-serif"

# Ảnh cho lưới, xếp theo nhịp NGOẠI - NỘI - NGOẠI - NỘI - NGOẠI để ảnh xe không
# dồn cả vào một hàng. Đường dẫn tính từ thư mục vehicle-media. Ô ĐẦU TIÊN là ô
# lớn tràn ngang nên phải là ảnh CÓ NỀN THẬT: ảnh cutout nền đen đặt vào đó thì
# chiếc xe trôi lơ lửng giữa một mảng đen, nhìn như ô ảnh bị lỗi.
#
# ĐÃ ĐỐI CHIẾU HAI LẦN: file có thật trong data/media/vehicle-media, VÀ có thật
# trên CDN (curl từng đường dẫn, phải trả 200). Kiểm cả hai là bắt buộc vì hai kho
# KHÔNG giống nhau: VF3/3..jpg và VF5/1..webp có trong máy nhưng không có trên
# CDN, đưa vào là khách nhận được ô ảnh vỡ.
#
# Đừng chép đại từ _GALLERY_BY_VEHICLE của site_catalog: danh sách đó đang trỏ vào
# vài file không tồn tại (VF3/exterior.png, VF5/3.webp...).
#
# VF6, VF7, VF8 đủ ảnh để giữ đúng nhịp trên.
_EMAIL_PHOTOS_BY_MODEL: dict[str, tuple[str, ...]] = {
    # VF3 và VF5 trên CDN chỉ có ảnh cutout, không có ảnh ngoại thất chụp ngoài đời.
    # VF3: ô lớn dùng bản nền sáng nên vẫn nổi trên nền đen, ba ô sau là dãy màu xe.
    # VF5: ô lớn dùng ảnh khoang lái, bốn ô sau là dãy màu xe.
    # Cần bổ sung ảnh có nền cho hai mẫu này.
    "VF3": ("VF3/2.png", "VF3/đỏ.png", "VF3/xám.png", "VF3/hồng.png"),
    "VF5": ("VF5/2.webp", "VF5/đỏ.webp", "VF5/trắng.webp", "VF5/xám.webp", "VF5/vàng đen.webp"),
    "VF6": (
        "VF6/VF6-Lifestyle-10.webp", "VF6/bottom-banner.webp", "VF6/VF6-Lifestyle-11.webp",
        "VF6/interior-vf6-2.jpg", "VF6/VF6-Lifestyle-12.webp",
    ),
    "VF7": (
        "VF7/vf7-passion.webp", "VF7/vf7-noi-that-overview.webp", "VF7/vf7-uu-diem-1.webp",
        "VF7/vf7-noi-that-compare-left.webp", "VF7/vf7-uu-diem-3.webp",
    ),
    "VF8": (
        "VF8/banner.webp", "VF8/interior-img1.webp", "VF8/thietkekdh.webp",
        "VF8/volang.webp", "VF8/journey.webp",
    ),
    # Ô lớn phải là ảnh có nền thật. VF9/CE18.webp là ảnh cutout nền đen, để làm ô
    # lớn thì chiếc xe trôi lơ lửng giữa một mảng đen, nhìn như ô ảnh bị lỗi.
    "VF9": (
        "VF9/charging-tag-line-bg.webp", "VF9/interior-first-sight.webp",
        "VF9/cs-charging-station.webp", "VF9/int-slide-1.webp", "VF9/int-slide-4.webp",
    ),
}

# Ảnh chìm sau card, sinh bằng backend/scripts/make_email_assets.py.
_WATERMARK_NAME = "email-watermark.jpg"

# Hai ô màu đặc dùng làm ẢNH NỀN, sinh bằng backend/scripts/make_email_assets.py.
#
# Đây là cách khoá cứng màu thư. Ứng dụng mail trên điện thoại tự đảo màu theo chế
# độ sáng/tối của máy, NHƯNG nó chỉ đảo màu khai báo bằng CSS, không đụng vào ảnh.
# Nền khai bằng background-color thì bị lật; nền lát bằng ô ảnh đặc thì không.
# Nhờ vậy logo giữ nguyên bản gốc chữ trắng nền trong suốt mà vẫn luôn nằm trên
# nền tối, và cả thư giữ đúng một bộ màu ở mọi chế độ.
#
# Vẫn giữ bgcolor song song làm lớp đỡ: nơi nào không đọc được ảnh nền qua cid:
# thì rơi về màu khai báo, tức là bằng đúng hiện trạng cũ chứ không tệ hơn.
_ASSETS_DIR = Path(__file__).with_name("assets")
_BG_BASE_CID = "vinfast-bg-base"
_BG_CARD_CID = "vinfast-bg-card"

# Ảnh logo, sinh cùng script trên.
#
# KHÔNG dùng lại vinfast-logo.png cho thư nền tối: file đó là bản logo MÀU ĐEN
# (#231F20) dựng cho nền sáng, đặt lên nền đen là chìm nghỉm. Dải này lấy khuôn từ
# chính file đó rồi tô trắng, hình dạng không đổi, và nướng sẵn nền tối phía sau.
_BAND_CID = "vinfast-logo-band"
_BAND_SMALL_CID = "vinfast-logo-band-small"


def _media_origin() -> str:
    """Gốc URL ảnh, rỗng nếu không dùng được trong email.

    Mặc định media_base_url là "/media" — đường dẫn tương đối. Trong trình duyệt
    thì chạy, trong hộp thư thì KHÔNG: thư không biết nó được mở từ tên miền nào.
    Nên chỉ nhận URL tuyệt đối; còn lại trả rỗng và thư bỏ luôn phần ảnh thay vì
    gửi cho khách một mớ ô ảnh vỡ.
    """
    base = get_settings().media_base_url.rstrip("/")
    return base if base.startswith(("http://", "https://")) else ""


def _media_exists(relative: str) -> bool:
    """Ảnh có nằm trong kho không.

    Kho ảnh nội bộ là bản đối chiếu duy nhất tra được lúc chạy. Nếu thư mục không
    tồn tại (bản triển khai chỉ dùng CDN) thì bỏ qua bước kiểm tra, tin vào danh
    sách đã soạn — thà thế còn hơn im lặng cắt sạch ảnh của mọi email.

    LƯU Ý: kiểm được ở đây KHÔNG có nghĩa là CDN cũng có. Hai kho không giống nhau.
    Danh sách _EMAIL_PHOTOS_BY_MODEL phải đối chiếu tay với CDN mỗi lần sửa; đây
    chỉ là lớp chắn thứ hai.
    """
    root = Path(get_settings().media_root) / "vehicle-media"
    if not root.is_dir():
        return True
    return (root / relative).is_file()


def _photo_urls(model_code: str) -> list[str]:
    origin = _media_origin()
    if not origin:
        return []
    photos = _EMAIL_PHOTOS_BY_MODEL.get((model_code or "").upper(), ())
    return [f"{origin}/vehicle-media/{quote(p)}" for p in photos if _media_exists(p)]


def _watermark_url(model_code: str) -> str:
    origin = _media_origin()
    code = (model_code or "").upper()
    relative = f"{code}/{_WATERMARK_NAME}"
    if not origin or not code or not _media_exists(relative):
        return ""
    return f"{origin}/vehicle-media/{quote(relative)}"


def _maps_url(row) -> str:
    """Toạ độ chính xác hơn tên, nên ưu tiên. Không có thì tra theo tên + địa chỉ."""
    lat, lng = row["showroom_lat"], row["showroom_lng"]
    if lat is not None and lng is not None:
        return f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
    query = " ".join(v for v in (row["showroom_name"], row["showroom_address"]) if v)
    return f"https://www.google.com/maps/search/?api=1&query={quote(query or 'VinFast')}"


def _no_orphan(text: str) -> str:
    """Dán hai chữ cuối lại với nhau bằng khoảng trắng không ngắt.

    Ô nhãn trong card rộng 40% và canh giữa, nên tên dài tự xuống dòng và hay bỏ
    lại đúng MỘT chữ ở hàng cuối: "VINFAST NGUYỄN VĂN" rồi "CỪ" đứng lẻ loi.

    Không đặt cứng cho một tên nào: chỉ cần chữ cuối luôn đi cùng chữ áp cuối là
    mọi tên đều hết rớt lẻ, dù dài ngắn ra sao. Tên chỉ có một chữ thì giữ nguyên.

    Trả về HTML nên phải escape TRƯỚC khi nối, đừng escape kết quả của hàm này.
    """
    words = (text or "").split()
    if len(words) < 2:
        return escape(text or "")
    return f'{escape(" ".join(words[:-1]))}&nbsp;{escape(words[-1])}'


def _balanced_address(address: str) -> str:
    """Ngắt địa chỉ thành hai dòng dài gần bằng nhau.

    Ô địa chỉ canh giữa nên để nó tự xuống dòng thì hay ra một dòng dài kín và một
    dòng cụt lủn hai ba chữ, bỏ lại mảng trống rất xấu. Chọn dấu phẩy nào chia ra
    hai vế cân nhất rồi cắt ở đó.
    """
    parts = [part.strip() for part in (address or "").split(",") if part.strip()]
    if len(parts) < 2:
        return escape(address or "")
    cut = min(range(1, len(parts)), key=lambda i: abs(len(", ".join(parts[:i])) - len(", ".join(parts[i:]))))
    return f'{escape(", ".join(parts[:cut]))},<br>{escape(", ".join(parts[cut:]))}'


def _vi_number(value) -> str:
    """Số kiểu Việt: dấu phẩy thập phân, số nguyên thì bỏ phần thập phân.

    Giá trị không phải số thì trả nguyên xi. Hai chỗ cần điều này: bản mẫu trong
    resources/mockups/ truyền vào chuỗi {{...}} để lộ ra đây là ô điền, và dữ liệu bẩn
    trong cơ sở dữ liệu thì cũng không được làm hỏng cả lượt gửi thư.
    """
    if value is None:
        return ""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number.is_integer():
        return str(int(number))
    return f"{number:.1f}".replace(".", ",")


def _vehicle_paragraph(row) -> str:
    """MỘT đoạn giới thiệu xe, dựng từ thông số THẬT trong cơ sở dữ liệu.

    Đoạn này nằm SAU card thông tin lịch hẹn. Khách mở thư ra cần biết lịch của
    mình trước, phần giới thiệu xe để sau, nên gói gọn trong một đoạn.

    Không đặt cứng câu chữ cho một mẫu xe nào. Thông số nào cơ sở dữ liệu không có
    thì bỏ hẳn mệnh đề đó ra khỏi câu, không đoán, không điền số mặc định.
    Và không nhắc giá: thư xác nhận lịch không phải chỗ bán hàng.
    """
    model = f"VinFast {row['model_name']}"
    seats = row["seat_count"]
    battery = _vi_number(row["battery_capacity_kwh"])
    drive_range = _vi_number(row["estimated_range_km"])
    power = _vi_number(row["motor_power_kw"])
    variant = row["variant_name"] or ""

    text = model
    text += f" là mẫu xe điện {seats} chỗ" if seats else " là mẫu xe điện"
    text += f", pin khả dụng {battery} kWh." if battery else "."

    # Ghép công suất và quãng đường vào một câu. Thông số nào thiếu thì bỏ hẳn
    # mệnh đề đó ra khỏi câu chứ không viết "không rõ" hay điền số mặc định.
    clauses = []
    if power:
        clauses.append(f"Bản {variant} mạnh {power} kW" if variant else f"Công suất {power} kW")
    if drive_range:
        clauses.append(f"đi được khoảng {drive_range} km cho một lần sạc đầy")
    if clauses:
        text += " " + ", ".join(clauses) + "."

    text += (
        " Mấy thứ này đọc trên giấy khó hình dung, ngồi vào ghế lái chạy một vòng là bạn"
        " thấy rõ nhất."
    )
    return text




# Khối <style>: giữ nguyên chuỗi thường, KHÔNG dùng f-string. CSS đầy dấu ngoặc
# nhọn, nhét vào f-string là phải nhân đôi từng cái, mã thành không đọc nổi.
#
# Ba nhóm trong này, đọc theo thứ tự quan trọng:
#   1. Lớp đè [data-ogsc]/[data-ogsb]: Outlook trên điện thoại gắn hai thuộc tính
#      này lên thẻ gốc sau khi nó đã đảo màu. Bắt được thì gán lại đúng màu ban
#      đầu. Phần tử nào có màu cũng phải mang một trong các lớp bg-* / t-*.
#   2. Hiệu ứng: mặc định HIỆN ĐỦ, chỉ mượn trạng thái mờ trong lúc chờ.
#   3. Media query cho điện thoại.
_CONFIRM_STYLE = """<style>
  :root { color-scheme: dark only; supported-color-schemes: dark only; }
  a { text-decoration: none; }
  img { -ms-interpolation-mode: bicubic; border: 0; outline: none; }
  body { margin: 0; padding: 0; width: 100% !important; }

  /* ══ ĐÈ LẠI MÀU KHI OUTLOOK ĐIỆN THOẠI TỰ ĐẢO ══════════════════════════════
     Outlook trên điện thoại gắn data-ogsc / data-ogsb lên thẻ gốc sau khi nó đã
     đảo màu. Bắt được thì gán lại đúng màu ban đầu. Phần tử nào có màu cũng phải
     mang một trong các lớp dưới đây, thiếu lớp là lớp đè không với tới. */
  [data-ogsc] .bg-base,  [data-ogsb] .bg-base  { background-color: #121212 !important; }
  [data-ogsc] .bg-card,  [data-ogsb] .bg-card  { background-color: #1E1E1E !important; }
  [data-ogsc] .bg-gold,  [data-ogsb] .bg-gold  { background-color: #F5C542 !important; }
  [data-ogsc] .t-white,  [data-ogsb] .t-white  { color: #FFFFFF !important; }
  [data-ogsc] .t-body,   [data-ogsb] .t-body   { color: #E0E0E0 !important; }
  [data-ogsc] .t-gold,   [data-ogsb] .t-gold   { color: #F5C542 !important; }
  [data-ogsc] .t-onGold, [data-ogsb] .t-onGold { color: #121212 !important; }
  [data-ogsc] .t-muted,  [data-ogsb] .t-muted  { color: #8A8A8A !important; }

  /* ══ HIỆU ỨNG ══════════════════════════════════════════════════════════════
     Mặc định mọi khối HIỆN ĐỦ, chỉ mượn trạng thái mờ trong lúc chờ nhờ
     fill-mode:backwards. Nơi nào cắt animation thì thư hiện thẳng bản tĩnh,
     không bao giờ mất chữ. */
  @keyframes vfFade { from { opacity: 0; } to { opacity: 1; } }
  @keyframes vfPulse {
    0%, 100% { box-shadow: 0 0 0 rgba(255, 210, 74, 0); }
    50%      { box-shadow: 0 0 20px rgba(255, 210, 74, 0.55); }
  }
  .a1, .a2, .a3, .a4, .a5, .a6 { animation: vfFade 0.7s ease-out backwards; }
  .a1 { animation-delay: 0.05s; }
  .a2 { animation-delay: 0.20s; }
  .a3 { animation-delay: 0.35s; }
  .a4 { animation-delay: 0.50s; }
  .a5 { animation-delay: 0.65s; }
  .a6 { animation-delay: 0.80s; }
  .btn-pulse { animation: vfPulse 2.6s ease-in-out 1.6s infinite; }
  @media (prefers-reduced-motion: reduce) {
    .a1, .a2, .a3, .a4, .a5, .a6, .btn-pulse { animation: none !important; }
  }

  @media only screen and (max-width: 600px) {
    /* Bảng ngoài cùng đặt width:600px + max-width:100%. Ô chứa nó co theo nội dung
       nên "100%" tự quy về đúng 600px và bảng KHÔNG co lại. Ép width:100% mới cắt được. */
    .container { width: 100% !important; }
    /* Chỉ đè đệm NGANG, giữ nguyên đệm dọc của từng khối. */
    .px  { padding-left: 16px !important; padding-right: 16px !important; }
    .px2 { padding-left: 18px !important; padding-right: 18px !important; }
    .px3 { padding-left: 20px !important; padding-right: 20px !important; }
    /* Số đo bằng font hệ thống (Helvetica/Arial đậm) ở bề ngang 320px, tức là
       khổ hẹp nhất còn gặp nhiều. Đây là chỗ dễ rớt chữ nhất vì hai dòng dưới
       đã ngắt sẵn bằng <br>; nếu chúng tự xuống dòng thêm lần nữa là rớt chữ.

         dòng                  chỗ có   cỡ đang dùng   rộng thật
         PHIẾU XÁC NHẬN         288        30px          269
         THÔNG TIN LỊCH HẸN     250        20px          222

       Bỏ webfont xong chữ hẹp hơn hẳn nên hai dòng này vừa thoải mái, không cần
       thêm ngưỡng cho máy hẹp nữa. Sửa cỡ chữ thì phải đo lại bảng này. */
    .h-page    { font-size: 30px !important; line-height: 40px !important; }
    .h-goldbar { font-size: 17px !important; line-height: 26px !important; }
    .h-card    { font-size: 20px !important; line-height: 30px !important; }
    /* Ô ảnh hẹp lại, chiều cao phải hạ theo cho đỡ méo. */
    .gimg-hero { height: 190px !important; }
    .gimg-half { height: 132px !important; }
    /* Hàng trong card xếp dọc, nhãn trên giá trị dưới, vẫn canh giữa.
       box-sizing BẮT BUỘC: ô vừa width:100% vừa có đệm ngang, thiếu nó thì ô rộng
       100% + đệm và đẩy cả thư tràn ngang. */
    .row-label { display: block !important; width: 100% !important; box-sizing: border-box !important; padding: 18px 0 6px 0 !important; }
    .row-value { display: block !important; width: 100% !important; box-sizing: border-box !important; padding: 0 !important; }
    .row-first { padding-top: 0 !important; }
    .btn-text { font-size: 11.5px !important; letter-spacing: 0.8px !important; }
    .btn-pad  { padding-left: 18px !important; padding-right: 18px !important; }
    .dual-btn-cell-left  { padding-right: 3px !important; }
    .dual-btn-cell-right { padding-left: 3px !important; }
    .dual-btn-pad { padding: 13px 5px !important; }
    .dual-btn-text { font-size: 11px !important; letter-spacing: 0.15px !important; white-space: nowrap !important; }
    .dual-btn-full { display: none !important; }
    .dual-btn-short { display: inline !important; }
    /* Căn đều ở bề ngang hẹp làm chữ giãn thưa loang lổ, trả về căn trái. */
    .just { text-align: left !important; }
    /* Card hẹp lại thì nửa chiếc xe chiếm gần hết nền, phải thu nhỏ. */
    .card-body { background-size: 78% auto !important; }
  }

</style>"""


def _confirmation_images() -> tuple[InlineImage, ...]:
    """Ảnh đính kèm inline: logo VinFast và hai ô nền.

    Logo có nền tối nướng sẵn, xem chú thích ở _BAND_CID.

    Thiếu file nào thì bỏ file đó: mất logo thì thư hiện chữ thay thế "VinFast",
    mất ô nền thì rơi về bgcolor. Cả hai trường hợp thư vẫn đọc được.
    """
    images = []
    for cid, name in (
        (_BAND_CID, "email-logo-band.png"),
        (_BAND_SMALL_CID, "email-logo-band-small.png"),
        (_BG_BASE_CID, "email-bg-base.png"),
        (_BG_CARD_CID, "email-bg-card.png"),
    ):
        try:
            data = (_ASSETS_DIR / name).read_bytes()
        except OSError:
            continue
        images.append(InlineImage(cid=cid, content=data))
    return tuple(images)


def _lock_colors(html: str) -> str:
    """Gắn !important vào mọi khai báo màu nội tuyến.

    Lớp khoá màu cuối cùng. Một số ứng dụng mail đảo màu bằng cách chèn thêm CSS
    của chúng đè lên thư; khai báo nội tuyến có !important thắng được lớp chèn đó.
    Không ăn thua với mọi ứng dụng, nhưng không tốn gì và đôi khi cứu được.

    Chỉ đụng vào thuộc tính style=, không đụng khối <style> ở đầu thư (khối đó đã
    tự có !important ở chỗ cần).
    """

    def fix(match: re.Match[str]) -> str:
        body = re.sub(
            r"\b(background-color|color)\s*:\s*([^;\"]+?)(?=;|$)",
            lambda m: f"{m.group(1)}:{m.group(2).strip()} !important",
            match.group(1),
        )
        return f'style="{body}"'

    return re.sub(r'style="([^"]*)"', fix, html)


def _tiled(cid: str, color: str) -> tuple[str, str]:
    """Cặp (thuộc tính HTML, mẩu style) để lát nền bằng ô ảnh.

    Trả cả `background="cid:..."` cho ứng dụng đọc thuộc tính HTML, lẫn
    background-image trong style. Luôn kèm background-color làm lớp đỡ.
    """
    return (
        f' bgcolor="{color}" background="cid:{cid}"',
        f"background-color:{color};background-image:url('cid:{cid}');background-repeat:repeat;",
    )


def _gold_button(url: str, label: str) -> str:
    """Nút hẹp canh giữa, chữ ĐEN trên nền vàng.

    Dùng _G_GOLD_BTN, SÁNG HƠN thanh vàng một nấc, cộng một đường mép trên nhạt.
    Trước đây nút và thanh tên khách cùng một màu; mảng vàng lớn của thanh hút hết
    mắt nên nút chìm nghỉm giữa thư. Tách sắc độ thì nút thành chỗ sáng nhất.

    Vàng đi với chữ đen, đổi sang chữ trắng là mất hết chất. Không kéo full width.
    Mảng vàng đặc cỡ này còn là thứ sống sót tốt nhất khi ứng dụng mail tự đảo màu.
    """
    return (
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" align="center" '
        f'bgcolor="{_G_GOLD_BTN}" class="btn-pulse bg-gold" style="background-color:{_G_GOLD_BTN};'
        f'border-radius:4px;border-top:1px solid {_G_GOLD_EDGE};">'
        f'<tr><td class="btn-pad" align="center" style="padding:17px 38px;">'
        f'<a href="{escape(url)}" class="btn-text t-onGold" style="display:block;font-family:{_G_BODY};'
        f"font-size:13.5px;line-height:18px;font-weight:700;color:{_G_BLACK};letter-spacing:1.6px;"
        f'text-transform:uppercase;text-decoration:none;">{escape(label)}</a>'
        "</td></tr></table>"
    )


def _invitation_action_buttons(site_url: str, invitation_url: str) -> str:
    """Two compact, email-safe CTAs that remain side by side on mobile."""

    def button(
        url: str,
        full_label: str,
        short_label: str,
        *,
        primary: bool,
    ) -> str:
        background = _G_GOLD_BTN if primary else _G_CARD
        color = _G_BLACK if primary else _G_GOLD_BTN
        pulse = " btn-pulse" if primary else ""
        background_class = "bg-gold" if primary else "bg-card"
        return (
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
            f'bgcolor="{background}" class="{background_class}{pulse}" style="width:100%;background-color:{background};'
            f'border:1px solid {_G_GOLD_BTN};border-radius:4px;">'
            f'<tr><td class="dual-btn-pad" align="center" style="padding:15px 8px;font-family:{_G_BODY};">'
            f'<a href="{escape(url)}" class="dual-btn-text" style="display:block;font-family:{_G_BODY};'
            f'font-size:12px;line-height:18px;font-weight:700;color:{color};letter-spacing:0.25px;'
            f'text-decoration:none;mso-line-height-rule:exactly;">'
            f'<span class="dual-btn-full" style="font-family:{_G_BODY};">{escape(full_label)}</span>'
            f'<span class="dual-btn-short" style="display:none;font-family:{_G_BODY};">{escape(short_label)}</span>'
            '</a></td></tr></table>'
        )

    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
        'style="width:100%;table-layout:fixed;"><tr>'
        '<td class="dual-btn-cell-left" width="45%" valign="middle" style="width:45%;padding-right:5px;">'
        f'{button(site_url, "Đến trang đặt lịch VinFast", "Trang đặt lịch", primary=False)}'
        '</td>'
        '<td class="dual-btn-cell-right" width="55%" valign="middle" style="width:55%;padding-left:5px;">'
        f'{button(invitation_url, "Xem thiệp mời của bạn", "Xem thiệp mời", primary=True)}'
        '</td></tr></table>'
    )


def _driver_preparation_link(url: str) -> str:
    """Preserve the private driver-chat capability without adding a third button."""
    return (
        f'<div class="t-body" align="center" style="padding:0 0 18px;font-family:{_G_BODY};'
        f'font-size:12px;line-height:19px;color:{_G_TEXT};">'
        f'<a href="{escape(url)}" class="t-gold" style="color:{_G_GOLD};text-decoration:underline;">'
        'Chuẩn bị riêng cho buổi lái thử cùng ViVi</a></div>'
    )


def _gold_row(label_html: str, value_html: str, *, first: bool) -> str:
    """Một hàng trong card: nhãn champagne bên trái, giá trị bên phải.

    CẢ HAI Ô canh giữa theo cả chiều ngang lẫn chiều dọc. Nhờ valign="middle",
    nhãn nằm đúng giữa khối hai ba dòng bên phải thay vì dính lên đỉnh. Các hàng
    tách nhau bằng khoảng đệm, KHÔNG kẻ vạch.

    Nhãn dùng đúng màu vàng chung của thư, xem lý do chọn ở chú thích _G_GOLD.

    `label_html` và `value_html` là HTML đã dựng sẵn, KHÔNG escape ở đây vì nhãn
    có thể mang <br> ngắt dòng. Chỗ gọi tự escape dữ liệu người dùng.
    """
    pad = "0 10px 20px" if first else "20px 10px"
    css_first = " row-first" if first else ""
    return (
        f'<tr><td class="row-label{css_first} t-gold" width="40%" valign="middle" align="center" '
        f'style="width:40%;padding:{pad};text-align:center;font-family:{_G_BODY};font-size:12px;'
        f'line-height:18px;font-weight:700;color:{_G_GOLD};letter-spacing:1.3px;'
        f'text-transform:uppercase;">{label_html}</td>'
        f'<td class="row-value t-body" width="60%" valign="middle" align="center" '
        f'style="width:60%;padding:{pad};text-align:center;font-family:{_G_BODY};font-size:13px;'
        f'line-height:21px;color:{_G_TEXT};">{value_html}</td></tr>'
    )


def _photo_grid(urls: list[str], model: str) -> str:
    """Lưới ảnh: một ảnh lớn tràn ngang, rồi hai hàng mỗi hàng hai ảnh.

    Bản trước xếp ba ảnh một hàng. Trên màn rộng thì được, nhưng xuống điện thoại
    mỗi ô chỉ còn khoảng 110px, nhìn không ra cái gì. Hai ảnh một hàng thì ô rộng
    gần 180px, đủ thấy.

    table-layout:fixed BẮT BUỘC. Thiếu nó, bảng auto-layout lấy chiều rộng GỐC của
    ảnh (có ảnh rộng 2880px) làm chiều rộng tối thiểu của ô và cả thư bị đẩy tràn
    ngang trên điện thoại. max-width:100% của ảnh không cứu được vì trình duyệt bỏ
    qua max-width phần trăm khi tính min-content của phần tử thay thế.

    Chiều cao đặt cứng + object-fit:cover. Để height:auto thì mỗi ảnh cao một kiểu
    tuỳ tỉ lệ gốc, lưới so le trông như vỡ. Outlook không hiểu object-fit nên sẽ
    kéo giãn ảnh; đổi lại lưới luôn thẳng hàng ở mọi nơi khác.

    Mỗi ô có viền mảnh để đọc ra là một khung ảnh chứ không phải mảng màu trôi
    trên nền đen. Mỗi ảnh có alt RIÊNG: lúc người nhận chưa bấm cho hiện ảnh thì
    năm dòng alt giống hệt nhau là vô dụng. Thẻ img mang luôn màu chữ để dòng alt
    đó đọc được trên nền tối.

    Số ảnh mỗi mẫu mỗi khác nên lưới co theo: một ô lớn rồi lần lượt từng hàng hai
    ô. Dư một ảnh lẻ thì bỏ ảnh đó chứ không để một ô đơn độc lệch hẳn sang trái.
    Không có ảnh nào thì bỏ hẳn lưới, không để ô trống.
    """
    if not urls:
        return ""
    # 1 ô lớn + các hàng đôi. 5 ảnh -> 1+2+2, 4 ảnh -> 1+2 (bỏ 1), 3 -> 1+2, 2 -> 1.
    pair_count = (len(urls) - 1) // 2

    # Mỗi ảnh một dòng alt riêng: lúc người nhận chưa bấm cho hiện ảnh, năm dòng
    # alt giống hệt nhau là vô dụng. Mẫu nào có nhiều ảnh hơn danh sách này thì
    # phần dư dùng nhãn chung.
    alts: tuple[str, ...] = (
        f"{model} nhìn từ bên ngoài",
        f"Khoang nội thất {model}",
        f"Chi tiết ngoại thất {model}",
        f"Khoang lái {model}",
        f"{model} trong đời sống hằng ngày",
    )
    alts += tuple(f"Ảnh {model}" for _ in range(max(0, len(urls) - len(alts))))
    style = (
        "display:block;width:100%;max-width:100%;height:{h}px;object-fit:cover;"
        f"border:1px solid #3A3222;color:{_G_GOLD};font-family:{_G_BODY};font-size:12px;"
    )

    def cell(index: int, width: str, height: int, css: str) -> str:
        return (
            f'<td width="{width}" style="width:{width};padding:3px;">'
            f'<img src="{escape(urls[index])}" width="100%" alt="{escape(alts[index])}" '
            f'class="{css}" style="{style.format(h=height)}"></td>'
        )

    table = (
        'table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
        'style="width:100%;table-layout:fixed;"'
    )
    rows = [f"<{table}><tr>{cell(0, '100%', 248, 'gimg-hero')}</tr></table>"]
    for pair in range(pair_count):
        left, right = 1 + pair * 2, 2 + pair * 2
        rows.append(
            f"<{table}><tr>{cell(left, '50%', 164, 'gimg-half')}"
            f"{cell(right, '50%', 164, 'gimg-half')}</tr></table>"
        )
    return '<tr><td class="px3 a6" style="padding:24px 21px 0;">' + "".join(rows) + "</td></tr>"


# ═══════════════════════════════════════════════════════════════════════════════
# KHUNG DÙNG CHUNG
# ═══════════════════════════════════════════════════════════════════════════════
# Mọi thư nền tối đều dựng từ ba mảnh dưới đây, nhờ vậy font, màu, khoảng cách và
# cách xuống dòng luôn giống nhau. Thêm loại thư mới thì viết thêm nội dung, ĐỪNG
# chép lại khung.


def _para_row(pad: str, body: str, css: str) -> str:
    """Một đoạn văn căn đều hai biên.

    `body` là HTML đã dựng sẵn, KHÔNG escape ở đây: đoạn mở đầu có thẻ <span> tô
    vàng tên xe bên trong. Chỗ gọi phải tự escape dữ liệu người dùng.

    Trên điện thoại lớp .just tự trả về căn trái, vì căn đều ở bề ngang hẹp làm
    chữ giãn thưa loang lổ.
    """
    return (
        f'<tr><td class="px3 {css} just t-body" style="padding:{pad} 24px 0;font-family:{_G_BODY};'
        f'font-size:15px;line-height:26px;font-weight:500;color:{_G_TEXT};'
        f'text-align:justify;">{body}</td></tr>'
    )


def _gold_text(text: str) -> str:
    """Tô vàng một cụm giữa dòng văn. Mỗi thư chỉ nên dùng MỘT lần.

    Dùng nhiều chỗ thì vàng mất tác dụng nhấn, đọc thành loang lổ.
    """
    return f'<span class="t-gold" style="color:{_G_GOLD};font-weight:700;">{escape(text)}</span>'


def _card_block(
    *,
    title_lines: tuple[str, str],
    rows_html: str,
    note_html: str,
    button_html: str,
    watermark_url: str,
) -> str:
    """Card thông tin: viền vàng, nền tối, ảnh chìm neo mép trái.

    Ảnh chìm phải được hạ sáng SẴN từ ngoài, email không có opacity cho ảnh nền.
    Luôn giữ bgcolor để nơi nào chặn ảnh nền (Outlook trên Windows) vẫn có nền
    tối và chữ vẫn đọc được.
    """
    card_attr_bg, card_style_bg = _tiled(_BG_CARD_CID, _G_CARD)
    if watermark_url:
        bg = (
            f"background-image:url('{escape(watermark_url)}');background-position:left bottom;"
            "background-repeat:no-repeat;background-size:58% auto;"
        )
        attr = f' background="{escape(watermark_url)}"'
    else:
        bg, attr = "", ""

    title = (
        f'<div class="h-card t-white" align="center" style="text-align:center;font-family:{_G_HEAD};'
        f'font-size:26px;line-height:38px;font-weight:700;color:#FFFFFF;letter-spacing:0.5px;'
        f'text-transform:uppercase;">%s</div>'
    )
    return f"""    <tr><td class="px a4" style="padding:34px 24px 0;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="bg-card"{card_attr_bg} style="width:100%;{card_style_bg}border:1px solid {_G_GOLD};border-radius:8px;">
        <tr><td class="px2 card-body"{attr} style="padding:32px 26px;background-color:{_G_CARD};{bg}">
          {title % escape(title_lines[0])}{title % escape(title_lines[1])}
          <div style="height:22px;line-height:22px;font-size:0;">&nbsp;</div>
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;table-layout:fixed;">{rows_html}</table>
          <div style="height:28px;line-height:28px;font-size:0;">&nbsp;</div>
          <div class="just t-body" style="text-align:justify;font-family:{_G_BODY};font-size:13.5px;line-height:23px;font-weight:500;color:{_G_TEXT};">
            {note_html}
          </div>
          <div style="height:26px;line-height:26px;font-size:0;">&nbsp;</div>
          {button_html}
        </td></tr>
      </table>
    </td></tr>"""


def _dark_document(
    *,
    title: str,
    preheader: str,
    headline_lines: tuple[str, str],
    bar_html: str,
    bar_size: str,
    bar_kind: str,
    show_nav: bool = True,
    blocks: str,
    footer_lines: tuple[str, ...],
    year: int,
) -> str:
    """Bộ khung của mọi thư nền tối: đầu thư, tiêu đề, thanh vàng, ruột, chân thư.

    `blocks` là phần ruột đã dựng sẵn thành các thẻ <tr>. Mỗi loại thư nhét gì
    vào đó tuỳ nội dung, còn khung thì không đổi.

    Khung ngoài cùng để TRONG SUỐT, chỉ khung 600px mới có nền tối. Nhờ vậy vùng
    tối rộng đúng bằng thanh vàng, không trải thành một biển đen trên màn rộng.
    """
    # Thanh ngay dưới tiêu đề có hai kiểu. "gold" là mảng vàng đặc chữ đen, dùng
    # cho thư báo tin vui. "muted" là thanh xám chữ trắng, dùng cho thư huỷ lịch:
    # đổ một mảng vàng rực lên đầu thư báo huỷ đọc ra như đang ăn mừng.
    if bar_kind == "none":
        bar = ""
    elif bar_kind == "muted":
        bar = (
            f'<tr><td class="h-goldbar a2 t-white" bgcolor="{_G_MUTED_BAR}" align="center" '
            f'style="background-color:{_G_MUTED_BAR};padding:13px 20px;font-family:{_G_HEAD};'
            f'font-size:{bar_size};line-height:32px;font-weight:700;color:#FFFFFF;'
            f'letter-spacing:0.5px;text-transform:uppercase;">{bar_html}</td></tr>'
        )
    else:
        bar = (
            f'<tr><td class="h-goldbar a2 bg-gold t-onGold" bgcolor="{_G_GOLD}" align="center" '
            f'style="background-color:{_G_GOLD};padding:13px 20px;font-family:{_G_HEAD};'
            f'font-size:{bar_size};line-height:32px;font-weight:700;color:{_G_BLACK};'
            f'letter-spacing:0.5px;text-transform:uppercase;">{bar_html}</td></tr>'
        )

    base_attr, base_style = _tiled(_BG_BASE_CID, _G_BLACK)
    nav_cell = (
        '<td width="25%" height="26" align="center" '
        'style="width:25%;height:26px;font-size:10px;line-height:26px;">&nbsp;</td>'
    )
    nav = (
        '<tr><td><table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'border="0" style="width:100%;"><tr>{nav_cell * 4}</tr></table></td></tr>'
        if show_nav
        else ""
    )
    foot = "".join(
        f'<div class="t-muted" style="font-family:{_G_BODY};font-size:12px;line-height:20px;'
        f'color:{_G_MUTED};">{line}</div>'
        for line in footer_lines
    )
    site = get_settings().public_site_url.rstrip("/")

    document = f"""<!doctype html>
<html lang="vi" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="x-apple-disable-message-reformatting">
<meta name="color-scheme" content="dark only">
<meta name="supported-color-schemes" content="dark only">
<title>{escape(title)}</title>
<!--[if mso]>
<style>*{{font-family:Arial,Helvetica,sans-serif !important;}}</style>
<xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml>
<![endif]-->
{_CONFIRM_STYLE}
</head>
<body style="margin:0;padding:0;background-color:transparent;">
<div style="display:none;max-height:0;overflow:hidden;mso-hide:all;font-size:1px;line-height:1px;color:{_G_BLACK};">
  {escape(preheader)}
</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:transparent;">
<tr><td align="center" style="padding:0;">
  <table role="presentation" class="container bg-base" width="600" cellpadding="0" cellspacing="0" border="0"{base_attr} style="width:600px;max-width:600px;{base_style}">

    <tr><td class="a1" style="padding:0;">
      <img src="cid:{_BAND_CID}" width="600" alt="VinFast" style="display:block;width:100%;max-width:600px;height:auto;">
    </td></tr>

    {nav}

    <tr><td class="px a2" align="center" style="padding:14px 24px 22px;">
      <div class="h-page t-white" style="font-family:{_G_HEAD};font-size:40px;line-height:50px;font-weight:700;color:#FFFFFF;letter-spacing:0.5px;text-transform:uppercase;">{escape(headline_lines[0])}<br>{escape(headline_lines[1])}</div>
    </td></tr>
    {bar}

{blocks}

    <tr><td class="a6" style="padding:40px 0 0;">
      <img src="cid:{_BAND_SMALL_CID}" width="600" alt="VinFast" style="display:block;width:100%;max-width:600px;height:auto;">
    </td></tr>
    <tr><td class="px a6" align="center" style="padding:20px 24px 42px;">
      {foot}
      <div style="height:16px;line-height:16px;font-size:0;">&nbsp;</div>
      <div style="font-family:{_G_BODY};font-size:12px;line-height:20px;">
        <a href="{escape(site)}/" class="t-gold" style="color:{_G_GOLD};text-decoration:underline;">Trang đặt lịch</a>
      </div>
      <div style="height:14px;line-height:14px;font-size:0;">&nbsp;</div>
      <div class="t-muted" style="font-family:{_G_BODY};font-size:11px;line-height:18px;color:#5C5C5C;">&copy; {year} VinFast</div>
    </td></tr>

  </table>
</td></tr>
</table>
</body>
</html>"""
    return document.replace("\n    \n", "\n\n")


# ═══════════════════════════════════════════════════════════════════════════════
# THƯ VỀ LỊCH HẸN — xác nhận, nhắc lịch, đổi giờ, huỷ
# ═══════════════════════════════════════════════════════════════════════════════
# Cả bốn loại dùng CHUNG một bộ khung và chung bảng thông tin lịch hẹn. Khác nhau
# đúng bốn chỗ gói trong _DarkCopy: tiêu đề, đoạn mở đầu, đoạn nhắc trong card,
# và nút. Thêm loại mới thì thêm một dòng vào _BOOKING_COPY.


@dataclass(frozen=True)
class _DarkCopy:
    headline: tuple[str, str]
    subject: str
    intro: str
    note: str
    button_label: str
    button_path: str
    # Câu mở của tin nhắn SMS. Tách riêng khỏi tiêu đề thư vì tiêu đề viết cho
    # mắt nhìn trên một mảng lớn ("Phiếu xác nhận lịch hẹn"), còn tin nhắn cần
    # một câu nói thẳng chuyện gì vừa xảy ra.
    sms_lead: str
    # Thư huỷ lịch KHÔNG kèm đoạn giới thiệu xe và lưới ảnh: khách vừa huỷ xong
    # mà thư còn khoe xe thì đọc ra rất vô duyên.
    show_vehicle: bool = True
    # Thanh ngay dưới tiêu đề luôn mang TÊN KHÁCH ở mọi loại thư. Đã thử cho nó
    # mang giờ hẹn hoặc mã lịch tuỳ loại, nhưng như vậy mỗi thư một kiểu, mở ra
    # không biết đang nhìn cái gì. Tên khách ở đúng một chỗ cố định thì thư nào
    # cũng đọc ra ngay là "thư này gửi cho mình".
    #
    # Chỉ có SẮC ĐỘ của thanh là đổi: "gold" cho thư báo tin, "muted" (xám) cho
    # thư huỷ lịch, vì đổ vàng rực lên đầu thư báo huỷ đọc ra như đang ăn mừng.
    bar_kind: str = "gold"
    # Nút phụ "Kiểm tra thông tin lịch của bạn" ở đầu thư. Thư huỷ không cần.
    show_check_button: bool = True
    # Tiêu đề hai dòng của card. Thư huỷ phải nói "lịch đã huỷ", không thể dùng
    # chung chữ "thông tin lịch hẹn" như thư báo tin.
    card_title: tuple[str, str] = ("ViVi gửi bạn", "thông tin lịch hẹn")
    # Dòng đầu chân thư, giải thích VÌ SAO người ta nhận được thư này. Mỗi loại
    # một lý do khác nhau. Bản trước dùng chung một câu "Bạn đã đăng ký lái thử
    # tại X" cho cả thư huỷ lịch — đọc lên vô lý, vừa báo huỷ xong lại nói vừa
    # đăng ký. Có {showroom} để thay tên showroom.
    footer_reason: str = "Bạn đã đăng ký lái thử tại {showroom}."


_BOOKING_COPY: dict[str, _DarkCopy] = {
    "booking_confirmation": _DarkCopy(
        headline=("Phiếu xác nhận", "lịch hẹn"),
        subject="Phiếu xác nhận lịch hẹn lái thử {model} - {code}",
        intro=(
            "ViVi xin trân trọng cảm ơn và thông báo, dựa trên thông tin đăng ký đặt lịch lái "
            "thử xe {model_gold}, lịch hẹn của bạn đã được đặt thành công. ViVi gửi đến bạn "
            "toàn bộ thông tin chi tiết của lịch hẹn ngay bên dưới, bạn xem qua và kiểm tra "
            "lại giúp ViVi nhé."
        ),
        note=(
            "Khi đến lịch hẹn, bạn nhớ mang theo giấy phép lái xe đúng với thông tin đã đăng ký. "
            "Nếu muốn đổi giờ, bạn quay lại trang đặt lịch để chọn khung giờ khác, ViVi luôn sẵn "
            "lòng hỗ trợ. ViVi rất mong được gặp và đồng hành cùng bạn trong buổi lái thử sắp tới."
        ),
        button_label="Đến trang đặt lịch VinFast",
        button_path="/",
        sms_lead="Lịch lái thử đã xác nhận.",
        footer_reason="Bạn nhận được thư này vì vừa đặt lịch lái thử tại {showroom}.",
    ),
    # Thư nhắc lịch cố ý NGẮN và khác hẳn thư xác nhận: bỏ đoạn giới thiệu xe và
    # lưới ảnh, đoạn mở đầu tô vàng GIỜ HẸN vì đó mới là thứ người ta cần liếc.
    # Người nhận thư này đã đọc thư xác nhận rồi.
    "reminder": _DarkCopy(
        headline=("ViVi nhắc bạn", "lịch lái thử"),
        subject="Nhắc lịch lái thử {model} - {code}",
        intro=(
            "Xin chào bạn, ViVi nhắc bạn có lịch hẹn với ViVi tại {showroom} vào {when_gold} để "
            "lái thử xe {model_gold}. ViVi gửi lại thông tin lịch hẹn ngay bên dưới, bạn xem qua "
            "giúp ViVi nhé."
        ),
        note=(
            "Bạn hãy đến showroom trước giờ hẹn khoảng 10-15 phút để ViVi cùng nhân viên hỗ trợ "
            "làm thủ tục cho bạn nhé. Khi đi bạn nhớ mang theo giấy phép lái xe đúng với thông "
            "tin bạn đã đăng ký với ViVi nha. ViVi và nhân viên rất mong được gặp và sẵn sàng hỗ "
            "trợ theo các yêu cầu của bạn."
        ),
        button_label="Đến trang đặt lịch VinFast",
        button_path="/",
        sms_lead="Nhắc lịch lái thử VinFast.",
        footer_reason="Bạn nhận được thư này vì đang có lịch lái thử tại {showroom}.",
        show_vehicle=False,
    ),
    # Thư đổi giờ: cái người ta cần thấy ngay là GIỜ MỚI, nên nó vào tiêu đề thư,
    # được tô vàng trong đoạn mở đầu, và trong card có thêm hàng "Giờ trước đây"
    # gạch ngang để đối chiếu. Hàng đó chỉ hiện khi tra được lịch cũ.
    "reschedule_confirmation": _DarkCopy(
        headline=("Lịch hẹn", "đã đổi giờ"),
        subject="Lịch lái thử {model} đã đổi sang {when} - {code}",
        intro=(
            "Xin chào bạn, ViVi đã đổi lịch lái thử xe {model_gold} sang khung giờ mới theo yêu "
            "cầu của bạn. Giờ hẹn mới là {when_gold}. Thông tin đầy đủ sau khi đổi nằm ngay bên "
            "dưới, bạn xem lại giúp ViVi nhé."
        ),
        note=(
            "Bạn nhớ mang theo giấy phép lái xe đúng với thông tin đã đăng ký. Nếu khung giờ mới "
            "vẫn chưa tiện, bạn quay lại trang đặt lịch để đổi tiếp, ViVi luôn sẵn lòng hỗ trợ."
        ),
        button_label="Đến trang đặt lịch VinFast",
        button_path="/",
        sms_lead="Lịch lái thử đã đổi giờ.",
        footer_reason="Bạn nhận được thư này vì vừa đổi giờ lịch lái thử tại {showroom}.",
    ),
    "booking_update": _DarkCopy(
        headline=("Lịch hẹn", "vừa cập nhật"),
        subject="Cập nhật lịch lái thử {model} - {code}",
        intro=(
            "Xin chào bạn, thông tin lịch lái thử xe {model_gold} của bạn vừa được cập nhật. "
            "ViVi gửi lại toàn bộ thông tin mới nhất ngay bên dưới, bạn xem qua giúp ViVi nhé."
        ),
        note=(
            "Bạn nhớ mang theo giấy phép lái xe đúng với thông tin đã đăng ký. Nếu có chỗ nào "
            "chưa đúng, bạn quay lại trang đặt lịch để chỉnh, ViVi luôn sẵn lòng hỗ trợ."
        ),
        button_label="Đến trang đặt lịch VinFast",
        button_path="/",
        sms_lead="Lịch lái thử vừa được cập nhật.",
        footer_reason="Bạn nhận được thư này vì lịch lái thử tại {showroom} vừa được cập nhật.",
    ),
    # Thư huỷ lịch là thư BÁO VIỆC, không phải thư mời. Vì vậy nó khác hẳn:
    #   - thanh trên đầu là XÁM chứ không phải mảng vàng. Đổ vàng rực lên đầu thư
    #     báo huỷ đọc ra như đang ăn mừng.
    #   - bỏ nút "Kiểm tra thông tin lịch của bạn": không còn lịch nào để kiểm.
    #   - bỏ đoạn giới thiệu xe và lưới ảnh.
    #   - card đổi tiêu đề thành "thông tin lịch đã huỷ", không dùng chung chữ
    #     "thông tin lịch hẹn" như thư báo tin.
    "cancellation_confirmation": _DarkCopy(
        headline=("Lịch hẹn", "đã huỷ"),
        subject="Đã huỷ lịch lái thử {model} - {code}",
        intro=(
            "Xin chào bạn, lịch lái thử xe {model_gold} đã được huỷ theo yêu cầu của bạn. Thông "
            "tin của lịch vừa huỷ được ViVi gửi đến bạn bên dưới, để bạn đối chiếu."
        ),
        note=(
            "Bạn đã huỷ lịch thành công, bạn không cần làm thêm bước nào nữa. Nhưng ViVi rất "
            "mong được gặp và hỗ trợ bạn, nên khi nào bạn sắp xếp được thời gian thì hãy vào "
            "trang đặt lịch và cho ViVi biết nhé. ViVi sẽ rất vui khi được đón tiếp bạn lần nữa."
        ),
        button_label="Đặt lịch lái thử mới",
        button_path="/booking",
        sms_lead="Lịch lái thử đã huỷ.",
        footer_reason="Bạn nhận được thư này vì vừa huỷ lịch lái thử tại {showroom}.",
        show_vehicle=False,
        bar_kind="muted",
        show_check_button=False,
        card_title=("ViVi gửi bạn", "thông tin lịch đã huỷ"),
    ),
}
# Ba mốc nhắc lịch dùng chung một bản chữ.
_BOOKING_COPY["reminder_24h"] = _BOOKING_COPY["reminder"]
_BOOKING_COPY["reminder_2h"] = _BOOKING_COPY["reminder"]


def _booking_facts(row, *, recipient_person_id: str | None = None) -> dict:
    """Bóc dữ liệu của một lịch hẹn ra đúng một chỗ, để bốn loại thư dùng chung."""
    start = parse_utc(row["start_at"]).astimezone(VIETNAM_TZ)
    # Lịch đổi giờ trỏ ngược về lịch cũ. Không phải lúc nào cũng tra được (lịch
    # cũ có thể đã bị xoá), nên mọi chỗ dùng đều phải chịu được giá trị rỗng.
    previous_when = ""
    try:
        raw_previous = row["previous_start_at"]
    except (KeyError, IndexError):
        raw_previous = None
    if raw_previous:
        previous = parse_utc(raw_previous).astimezone(VIETNAM_TZ)
        previous_when = (
            f"{previous.strftime('%H:%M')} · {WEEKDAYS_VI[previous.weekday()]}, "
            f"{previous.strftime('%d/%m/%Y')}"
        )

    driver = row["driver_name"] or row["booker_name"] or "Quý khách"
    booker = row["booker_name"] or driver
    showroom = row["showroom_name"] or "Showroom VinFast"
    is_booker_recipient = bool(
        recipient_person_id
        and str(recipient_person_id) == str(row["booker_person_id"] or "")
    )
    recipient_name = booker if is_booker_recipient else driver
    recipient_email = row["booker_email"] if is_booker_recipient else row["driver_email"]
    recipient_phone = row["booker_phone"] if is_booker_recipient else row["driver_phone"]

    # Tên mẫu xe trong cơ sở dữ liệu KHÔNG nhất quán: bản seed thật ghi "VF 9",
    # còn dữ liệu test ghi sẵn "VinFast VF 6". Ghép tiền tố vô điều kiện là ra
    # "VinFast VinFast VF 6" trong hộp thư khách. Chỉ ghép khi chưa có.
    model_name = (row["model_name"] or "").strip()
    if not model_name.lower().startswith("vinfast"):
        model_name = f"VinFast {model_name}".strip()

    contact = [_no_orphan(driver)]
    if row["driver_email"]:
        contact.append(escape(row["driver_email"]))
    if row["driver_phone"]:
        contact.append(escape(row["driver_phone"]))
    # Người đặt hộ thì phải hiện cả hai tên, nếu không khách mở thư ra thấy tên
    # người khác trên thanh vàng mà không hiểu vì sao.
    if booker != driver:
        contact.append(f"Người đặt: {_no_orphan(booker)}")

    # Lịch chưa phân công thì KHÔNG được ghép tên giả vào câu. Bản trước ghép
    # "liên hệ nhân viên VinFast sẽ liên hệ" — câu vỡ, đọc ra là lỗi hệ thống.
    staff_name = row["staff_name"] or ""
    staff_phone = row["staff_phone"] or ""
    if staff_name:
        staff = [_no_orphan(staff_name)]
        if staff_phone:
            staff.append(escape(staff_phone))
        support = f"nhân viên {escape(staff_name)}"
        if staff_phone:
            support += f" theo số {escape(staff_phone)}"
    else:
        staff = ["Showroom sẽ liên hệ với bạn", "trước buổi lái thử"]
        support = f"showroom {escape(showroom)}"

    return {
        "start": start,
        # Hai cách viết giờ hẹn. Bản có dấu chấm giữa dùng cho BẢNG, nơi nó đứng
        # một mình nên dấu chấm đọc ra là dấu ngăn. Bản văn xuôi dùng khi giờ hẹn
        # nằm giữa câu, ở đó dấu chấm giữa đọc rất cợn.
        "when": f"{start.strftime('%H:%M')} · {WEEKDAYS_VI[start.weekday()]}, {start.strftime('%d/%m/%Y')}",
        "when_prose": f"{start.strftime('%H:%M')} {WEEKDAYS_VI[start.weekday()]}, ngày {start.strftime('%d/%m/%Y')}",
        "previous_when": previous_when,
        "code": row["booking_code"] or "-",
        "model": model_name,
        "driver": driver,
        "recipient_name": recipient_name,
        "recipient_email": recipient_email,
        "recipient_phone": recipient_phone,
        "showroom": showroom,
        "contact_lines": contact,
        "staff_lines": staff,
        "support": support,
        "staff_name": staff_name,
        "staff_phone": staff_phone,
    }


def _plain_staff_line(facts: dict) -> str:
    """Dòng nhân viên hỗ trợ cho bản chữ thuần. Chưa phân công thì không ghép tên giả."""
    if not facts["staff_name"]:
        return "Nhân viên hỗ trợ: showroom sẽ liên hệ với bạn trước buổi lái thử"
    line = f"Nhân viên hỗ trợ: {facts['staff_name']}"
    return f"{line} - {facts['staff_phone']}" if facts["staff_phone"] else line


def render_booking_dark_email(
    notification_type: str,
    row,
    *,
    driver_invite_url: str | None = None,
    recipient_person_id: str | None = None,
) -> RenderedEmail:
    """Thư về lịch hẹn, cá nhân hoá theo đúng lịch của khách.

    Mọi thứ lấy từ `row` của _render_notification: tên và liên hệ của khách,
    showroom cùng địa chỉ và toạ độ, mẫu xe và phiên bản cùng thông số, nhân viên
    phụ trách, giờ hẹn. Ảnh xe chọn theo mã mẫu xe. KHÔNG có gì đặt cứng theo một
    khách hay một mẫu xe cụ thể.

    `driver_invite_url` chỉ có giá trị khi người đặt KHÁC người lái. Khi đó CTA
    chính của thư gửi cho NGƯỜI LÁI trở thành link mời vào trò chuyện với ViVi,
    để họ nói nhu cầu riêng của mình chứ không phải nghe lại qua người đặt hộ.

    Bản xem trước sinh bằng backend/scripts/preview_confirmation_email.py.
    """
    copy = _BOOKING_COPY[notification_type]
    f = _booking_facts(row, recipient_person_id=recipient_person_id)
    site = get_settings().public_site_url.rstrip("/")
    # Email của driver riêng dùng chính CTA chính của phiếu xác nhận để vào
    # cuộc trò chuyện đã xác thực. Booker (và trường hợp booker = driver) vẫn
    # dùng nguyên nút/trang đặt lịch của template mới.
    primary_button_url = driver_invite_url or f"{site}{copy.button_path}"
    primary_button_label = (
        "Chuẩn bị lái thử cùng ViVi" if driver_invite_url else copy.button_label
    )
    invitation_url = (
        public_invitation_url(f["code"])
        if notification_type in {
            "booking_confirmation",
            "reschedule_confirmation",
            "reminder",
            "reminder_24h",
            "reminder_2h",
            "booking_update",
        }
        and f["code"] != "-"
        else ""
    )

    address_html = (
        f'<a href="{escape(_maps_url(row))}" class="t-body" style="color:{_G_TEXT};'
        f'text-decoration:underline;">{_balanced_address(row["showroom_address"] or f["showroom"])}</a>'
    )
    # Thư đổi giờ mới có hàng "Giờ trước đây". Gạch ngang và để màu xám: mắt lướt
    # qua là biết ngay dòng nào đã cũ, không phải đọc kỹ mới hiểu.
    previous_row = ""
    if notification_type == "reschedule_confirmation" and f["previous_when"]:
        previous_row = _gold_row(
            "Giờ trước đây",
            f'<span style="color:{_G_MUTED};text-decoration:line-through;">'
            f'{escape(f["previous_when"])}</span>',
            first=False,
        )

    rows_html = "".join(
        (
            _gold_row("Mã lịch hẹn", escape(f["code"]), first=True),
            previous_row,
            _gold_row(
                "Giờ hẹn mới" if previous_row else "Thời gian hẹn",
                escape(f["when"]),
                first=False,
            ),
            _gold_row(_no_orphan(f["showroom"]), address_html, first=False),
            _gold_row("Thông tin cá nhân", "<br>".join(f["contact_lines"]), first=False),
            # Ngắt dòng SẴN: để nhãn tự xuống dòng thì trên điện thoại chữ BẠN
            # rớt lại một mình một hàng.
            _gold_row("Thông tin nhân viên<br>hỗ trợ của bạn", "<br>".join(f["staff_lines"]), first=False),
        )
    )

    intro = copy.intro.format(
        model_gold=_gold_text(f["model"]),
        showroom=escape(f["showroom"]),
        when=escape(f["when_prose"]),
        when_gold=_gold_text(f["when_prose"]),
    )
    blocks = [_para_row("28px", intro, "a3")]
    if copy.show_check_button:
        blocks.append(
            f'    <tr><td class="px a3" align="center" style="padding:28px 24px 0;">'
            f'{_gold_button(f"{site}/booking", "Kiểm tra thông tin lịch của bạn")}</td></tr>'
        )
    card_buttons = _gold_button(primary_button_url, primary_button_label)
    if invitation_url:
        card_buttons = (
            (_driver_preparation_link(driver_invite_url) if driver_invite_url else "")
            + _invitation_action_buttons(f"{site}/", invitation_url)
        )
    blocks.append(
        _card_block(
            title_lines=copy.card_title,
            rows_html=rows_html,
            note_html=copy.note,
            button_html=card_buttons,
            watermark_url=_watermark_url(row["model_code"]),
        )
    )

    if copy.show_vehicle:
        blocks.append(_para_row("38px", escape(_vehicle_paragraph(row)), "a5"))
        blocks.append(_photo_grid(_photo_urls(row["model_code"]), f["model"]))

    subject = copy.subject.format(model=f["model"], code=f["code"], when=f["when_prose"])
    html = _dark_document(
        title=f"{copy.headline[0]} {copy.headline[1]} | VinFast",
        preheader=f"{copy.headline[0]} {copy.headline[1]}: {f['model']} lúc {f['when']}.",
        headline_lines=copy.headline,
        bar_html=escape(f["recipient_name"]),
        bar_size="22px",
        bar_kind=copy.bar_kind,
        blocks="\n\n".join(b for b in blocks if b),
        footer_lines=(
            copy.footer_reason.format(showroom=escape(f["showroom"])),
            "Đây là thư gửi tự động, bạn vui lòng không trả lời thư này.",
            f"Nếu bạn cần hỗ trợ, bạn hãy liên hệ {f['support']}.",
        ),
        year=f["start"].year,
    )

    plain_lines = [
        f"{copy.headline[0]} {copy.headline[1]}".upper(),
        f"Khách: {f['recipient_name']}",
        "",
        f"Mã lịch hẹn: {f['code']}",
        f"Thời gian hẹn: {f['when']}",
        f"Xe lái thử: {f['model']} {row['variant_name'] or ''}".strip(),
        "",
        f"Showroom: {f['showroom']}",
        f"Địa chỉ: {row['showroom_address'] or '-'}",
        f"Bản đồ: {_maps_url(row)}",
        "",
        f"Email: {f['recipient_email'] or '-'}",
        f"Điện thoại: {f['recipient_phone'] or '-'}",
        _plain_staff_line(f),
        "",
        f"Trang đặt lịch VinFast: {site}/",
    ]
    if invitation_url:
        plain_lines.append(f"Xem thiệp mời của bạn: {invitation_url}")
    if driver_invite_url:
        plain_lines.append(f"Chuẩn bị riêng cùng ViVi: {driver_invite_url}")
    plain_lines.append("Đây là thư gửi tự động, bạn vui lòng không trả lời thư này.")
    plain = "\n".join(plain_lines)
    sms = (
        f"{copy.sms_lead} Mã {f['code']}, {f['when']}, {f['model']} tại {f['showroom']}. "
        "Chi tiết đầy đủ đã gửi vào email của bạn."
    )
    return RenderedEmail(
        subject=subject,
        plain_text=plain,
        html=_lock_colors(html),
        inline_images=_confirmation_images(),
        sms_text=sms,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# THƯ MÃ XÁC THỰC
# ═══════════════════════════════════════════════════════════════════════════════
# Dùng chung khung, font và màu với thư lịch hẹn. Khác ở ba chỗ:
#   - Thanh vàng mang chính MÃ XÁC THỰC chứ không phải tên khách. Đây là thứ duy
#     nhất người nhận cần đọc, đặt lên mảng vàng đặc là chỗ đập vào mắt nhất thư.
#   - Ảnh chìm là xe Lạc Hồng, không gắn với mẫu xe nào vì lúc gửi mã thì khách
#     còn chưa chọn xe.
#   - Không có lưới ảnh và không có đoạn giới thiệu xe.

_LAC_HONG_WATERMARK = "email/lac-hong-watermark.jpg"


def _lac_hong_url() -> str:
    """Ảnh chìm Lạc Hồng cho thư mã xác thực. Không có thì card hiện nền tối trơn."""
    origin = _media_origin()
    if not origin:
        return ""
    root = Path(get_settings().media_root)
    if root.is_dir() and not (root / _LAC_HONG_WATERMARK).is_file():
        return ""
    return f"{origin}/{quote(_LAC_HONG_WATERMARK)}"


def render_otp_email(*, code: str, expires_in_seconds: int) -> RenderedEmail:
    """Thư mã xác thực. Cố ý ĐƠN GIẢN, không bê nguyên bố cục thư lịch hẹn sang.

    Thư này chỉ có một việc: đưa sáu chữ số cho người ta chép. Nhét thanh nav,
    bảng năm hàng và lưới ảnh vào thì mã bị chôn giữa một đống thứ không ai đọc.
    Ở đây chỉ còn logo, một câu, một khối mã, một dòng nhắc bảo mật.

    Font, màu và bộ khung vẫn lấy nguyên từ thư xác nhận nên vẫn cùng một nhà.
    """
    minutes = max(1, expires_in_seconds // 60)
    site = get_settings().public_site_url.rstrip("/")
    card_attr_bg, card_style_bg = _tiled(_BG_CARD_CID, _G_CARD)

    watermark = _lac_hong_url()
    if watermark:
        wm_style = (
            f"background-image:url('{escape(watermark)}');background-position:left bottom;"
            "background-repeat:no-repeat;background-size:58% auto;"
        )
        wm_attr = f' background="{escape(watermark)}"'
    else:
        wm_style, wm_attr = "", ""

    # Khối mã: chữ số phóng thật to và giãn rộng để chép tay không nhầm 0 với O.
    code_panel = f"""    <tr><td class="px a3" style="padding:30px 24px 0;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="bg-card"{card_attr_bg} style="width:100%;{card_style_bg}border:1px solid {_G_GOLD};border-radius:8px;">
        <tr><td align="center"{wm_attr} style="padding:34px 24px;background-color:{_G_CARD};{wm_style}">
          <div class="t-gold" style="font-family:{_G_BODY};font-size:12px;line-height:18px;font-weight:700;color:{_G_GOLD};letter-spacing:1.4px;text-transform:uppercase;">Mã xác thực của bạn</div>
          <div style="height:14px;line-height:14px;font-size:0;">&nbsp;</div>
          <div class="h-code t-gold" style="font-family:{_G_HEAD};font-size:44px;line-height:52px;font-weight:700;color:{_G_GOLD};letter-spacing:10px;">{escape(code)}</div>
          <div style="height:12px;line-height:12px;font-size:0;">&nbsp;</div>
          <div class="t-muted" style="font-family:{_G_BODY};font-size:13px;line-height:20px;color:{_G_MUTED};">Hiệu lực trong {minutes} phút</div>
        </td></tr>
      </table>
    </td></tr>"""

    blocks = "\n\n".join(
        (
            _para_row(
                "26px",
                (
                    "Xin chào bạn, ViVi gửi bạn mã xác thực để hoàn tất bước xác thực của bạn. "
                    f"Mã có hiệu lực trong {_gold_text(f'{minutes} phút')}, bạn nhập sớm giúp "
                    "ViVi nhé."
                ),
                "a2",
            ),
            code_panel,
            _para_row(
                "26px",
                (
                    "ViVi không bao giờ hỏi mã này qua điện thoại hay tin nhắn. Bạn vui lòng "
                    "không chia sẻ mã cho bất kỳ ai, kể cả người xưng là nhân viên VinFast. Nếu "
                    "bạn không phải người yêu cầu mã, bạn bỏ qua thư này giúp ViVi, mã sẽ tự "
                    "hết hiệu lực."
                ),
                "a4",
            ),
        )
    )

    html = _dark_document(
        title="Mã xác thực đặt lịch lái thử | VinFast",
        preheader=f"Mã xác thực của bạn là {code}, hiệu lực {minutes} phút.",
        headline_lines=("Mã xác thực", "đặt lịch lái thử"),
        bar_html="",
        bar_size="22px",
        # Không có thanh trên đầu và không có thanh nav: thư này càng gọn càng tốt.
        bar_kind="none",
        show_nav=False,
        blocks=blocks,
        footer_lines=(
            "Bạn nhận được thư này vì có yêu cầu xác thực trên trang đặt lịch lái thử VinFast.",
            "Đây là thư gửi tự động, bạn vui lòng không trả lời thư này.",
            "Vui lòng không chia sẻ mã xác thực với bất kỳ ai.",
        ),
        year=datetime.now(VIETNAM_TZ).year,
    )

    plain = "\n".join(
        (
            "MÃ XÁC THỰC ĐẶT LỊCH LÁI THỬ VINFAST",
            "",
            f"Mã xác thực: {code}",
            f"Hiệu lực trong: {minutes} phút",
            "",
            "ViVi không bao giờ hỏi mã này qua điện thoại hay tin nhắn.",
            "Vui lòng không chia sẻ mã cho bất kỳ ai.",
            "Nếu bạn không phải người yêu cầu mã, bạn bỏ qua thư này, mã sẽ tự hết hiệu lực.",
            "",
            f"Trang đặt lịch VinFast: {site}/",
            "Đây là thư gửi tự động, bạn vui lòng không trả lời thư này.",
        )
    )
    return RenderedEmail(
        subject="Mã xác thực đặt lịch lái thử VinFast",
        plain_text=plain,
        html=_lock_colors(html),
        inline_images=_confirmation_images(),
        sms_text=f"Ma xac thuc VinFast: {code}. Hieu luc {minutes} phut. Khong chia se cho bat ky ai.",
    )
