from pathlib import Path

import pytest
from src.services.booking.email_templates import (
    _BOOKING_COPY,
    render_booking_dark_email,
)
from src.services.booking.notifications import (
    InMemoryMessagingProvider,
)


# test case of Chau + kiểm tra dispatcher chỉ gửi notification đã đến hạn và lưu metadata provider
def test_dispatch_due_notifications_sends_due_confirmation(booking_service, booking_db, confirmed_booking_factory):
    booking = confirmed_booking_factory(notification_plan_patch={"email_enabled": 0, "sms_enabled": 1})
    provider = InMemoryMessagingProvider()
    booking_service.messaging_provider = provider

    result = booking_service.dispatch_due_notifications()

    assert result == {"claimed": 1, "sent": 1, "failed": 0, "is_mock": True}
    assert len(provider.messages) == 1
    assert provider.messages[0]["channel"] == "sms"
    assert provider.messages[0]["destination"] == "0901234567"
    assert "Lich lai thu da xac nhan" in provider.messages[0]["body"] or "Lịch lái thử đã xác nhận" in provider.messages[0]["body"]
    assert booking["confirmed"]["booking_code"] in provider.messages[0]["body"]
    with booking_db.connect() as connection:
        sent = connection.execute(
            "SELECT status,attempt_count,provider_name,provider_status,provider_message_id,"
            "provider_response_json,error_message FROM notification_jobs "
            "WHERE booking_id=? AND notification_type='booking_confirmation'",
            (booking["booking_id"],),
        ).fetchone()
        future_count = connection.execute(
            "SELECT count(*) AS total FROM notification_jobs WHERE booking_id=? AND status='pending'",
            (booking["booking_id"],),
        ).fetchone()["total"]

    assert sent["status"] == "sent"
    assert sent["attempt_count"] == 1
    assert sent["provider_name"] == "mock_sms"
    assert sent["provider_status"] == "mocked"
    assert sent["provider_message_id"].startswith("mock_")
    assert sent["provider_response_json"] == '{"accepted": true}'
    assert sent["error_message"] is None
    assert future_count == 2


# test case of Chau + kiểm tra job đã gửi không bị gửi trùng ở lần dispatcher kế tiếp
def test_dispatch_does_not_resend_sent_notification(booking_service, confirmed_booking_factory):
    confirmed_booking_factory(notification_plan_patch={"email_enabled": 0, "sms_enabled": 1})
    provider = InMemoryMessagingProvider()
    booking_service.messaging_provider = provider

    first = booking_service.dispatch_due_notifications()
    second = booking_service.dispatch_due_notifications()

    assert first["sent"] == 1
    assert second == {"claimed": 0, "sent": 0, "failed": 0, "is_mock": True}
    assert len(provider.messages) == 1


# test case of Chau + kiểm tra batch size giới hạn đúng số job được claim trong một lượt
def test_dispatch_respects_batch_size(booking_service, booking_db, confirmed_booking_factory):
    booking = confirmed_booking_factory(notification_plan_patch={"email_enabled": 0, "sms_enabled": 1})
    with booking_db.transaction(immediate=True) as connection:
        connection.execute(
            "UPDATE notification_jobs SET scheduled_at=? WHERE booking_id=?",
            (booking_service.now().isoformat(), booking["booking_id"]),
        )
    provider = InMemoryMessagingProvider()
    booking_service.messaging_provider = provider

    result = booking_service.dispatch_due_notifications(batch_size=2)

    assert result["claimed"] == 2
    assert result["sent"] == 2
    assert len(provider.messages) == 2
    with booking_db.connect() as connection:
        statuses = connection.execute(
            "SELECT status,count(*) AS total FROM notification_jobs WHERE booking_id=? GROUP BY status",
            (booking["booking_id"],),
        ).fetchall()
    assert {row["status"]: row["total"] for row in statuses} == {"pending": 1, "sent": 2}


# test case of Chau + kiểm tra thiếu địa chỉ nhận sẽ retry rồi chuyển failed khi hết số lần thử
def test_missing_recipient_destination_retries_then_fails(booking_service, booking_db, confirmed_booking_factory):
    booking = confirmed_booking_factory(notification_plan_patch={"email_enabled": 0, "sms_enabled": 1})
    with booking_db.transaction(immediate=True) as connection:
        connection.execute(
            "UPDATE people SET phone=NULL,email=NULL WHERE id=(SELECT driver_person_id FROM bookings WHERE id=?)",
            (booking["booking_id"],),
        )
        connection.execute(
            "UPDATE notification_jobs SET max_attempts=2 "
            "WHERE booking_id=? AND notification_type='booking_confirmation'",
            (booking["booking_id"],),
        )

    first = booking_service.dispatch_due_notifications()
    second = booking_service.dispatch_due_notifications()

    assert first == {"claimed": 1, "sent": 0, "failed": 1, "is_mock": True}
    assert second == {"claimed": 1, "sent": 0, "failed": 1, "is_mock": True}
    with booking_db.connect() as connection:
        row = connection.execute(
            "SELECT status,attempt_count,error_message FROM notification_jobs "
            "WHERE booking_id=? AND notification_type='booking_confirmation'",
            (booking["booking_id"],),
        ).fetchone()
    assert row["status"] == "failed"
    assert row["attempt_count"] == 2
    assert row["error_message"] == "recipient_channel_unavailable"


class _ExplodingProvider:
    def send_message(self, *, channel, destination, body):
        raise RuntimeError("provider unavailable")


# test case of Chau + kiểm tra lỗi provider được cô lập và job còn khả năng retry thay vì kẹt processing
def test_provider_exception_does_not_crash_dispatcher_or_stick_job(
    booking_service, booking_db, confirmed_booking_factory
):
    booking = confirmed_booking_factory(notification_plan_patch={"email_enabled": 0, "sms_enabled": 1})
    booking_service.messaging_provider = _ExplodingProvider()

    result = booking_service.dispatch_due_notifications()

    assert result["failed"] == 1
    with booking_db.connect() as connection:
        row = connection.execute(
            "SELECT status,attempt_count FROM notification_jobs "
            "WHERE booking_id=? AND notification_type='booking_confirmation'",
            (booking["booking_id"],),
        ).fetchone()
    assert row["status"] in {"pending", "failed"}
    assert row["attempt_count"] == 1


# Thư xác nhận là bản nền đen nhấn vàng, dựng theo resources/mockups/email-phieu-xac-nhan-awe.html.
# Ba nhóm kiểm tra dưới đây khoá đúng ba thứ từng hỏng khi dựng: dữ liệu phải là
# của chính lịch vừa xác nhận, kênh SMS không được dùng chung chữ của email, và
# các loại thông báo khác không được đội lốt thư xác nhận.
def test_confirmation_email_is_personalised(booking_service, confirmed_booking_factory):
    booking = confirmed_booking_factory(notification_plan_patch={"email_enabled": 1, "sms_enabled": 0})
    provider = InMemoryMessagingProvider()
    booking_service.messaging_provider = provider

    booking_service.dispatch_due_notifications()

    message = provider.messages[0]
    html = message["html_body"]
    code = booking["confirmed"]["booking_code"]

    assert message["channel"] == "email"
    assert code in message["subject"]
    # Dữ liệu của đúng lịch này, không phải chữ mẫu đặt cứng trong template.
    assert code in html
    assert "Huynh Thi Hai Chau" in html
    assert "chau@example.test" in html
    # Thông số xe đọc từ cơ sở dữ liệu chứ không đặt cứng, kể cả số chỗ ngồi.
    assert "5 chỗ" in html and "59,6 kWh" in html
    # Logo giữ nguyên file gốc, cộng hai ô nền lát. Thiếu ô nền thì nền thư quay
    # về khai báo bằng CSS và bị ứng dụng mail đảo màu theo chế độ máy.
    assert [image.cid for image in message["inline_images"]] == [
        "vinfast-logo-band",
        "vinfast-logo-band-small",
        "vinfast-bg-base",
        "vinfast-bg-card",
    ]
    # Năm lớp khoá màu phải còn nguyên.
    assert "cid:vinfast-logo-band" in html          # logo trắng, nền tối nướng sẵn
    # KHÔNG được nạp webfont: Google Fonts nạp thiếu bộ tiếng Việt trên điện thoại,
    # chữ có dấu rơi sang font khác từng ký tự một.
    assert "fonts.googleapis.com" not in html
    # Vùng tối giới hạn đúng bằng bề ngang thư, khung ngoài phải trong suốt.
    # (_lock_colors gắn thêm !important vào mọi khai báo màu nội tuyến)
    assert 'border="0" style="background-color:transparent !important;"' in html
    assert "url('cid:vinfast-bg-base')" in html     # nền thư lát bằng ô ảnh
    assert "url('cid:vinfast-bg-card')" in html     # nền card lát bằng ô ảnh
    assert 'content="dark only"' in html            # Apple Mail thôi tự đổi màu
    assert "[data-ogsc]" in html                    # lớp đè cho Outlook điện thoại
    assert "background-color:#121212 !important" in html
    # Chống rớt chữ: ba chỗ ngắt dòng sẵn.
    assert "Phiếu xác nhận<br>lịch hẹn" in html
    assert "Thông tin nhân viên<br>hỗ trợ của bạn" in html
    # Bộ màu vàng đen: nền Rich Black, một màu vàng duy nhất cho cả nền lẫn chữ.
    assert "#121212" in html and "#F5C542" in html
    # Mail xác nhận có đúng hai CTA nằm cùng hàng: trang đặt lịch và thiệp mời.
    assert "Đến trang đặt lịch VinFast" in html
    assert "Xem thiệp mời của bạn" in html
    assert "/invitation/v1." in html
    assert "Xem thiệp mời của bạn:" in message["body"]
    # Thư xác nhận lịch không phải chỗ bán hàng.
    assert "giá" not in html.lower().split("<body")[1]


def test_confirmation_sms_uses_short_text(booking_service, confirmed_booking_factory):
    confirmed_booking_factory(notification_plan_patch={"email_enabled": 0, "sms_enabled": 1})
    provider = InMemoryMessagingProvider()
    booking_service.messaging_provider = provider

    booking_service.dispatch_due_notifications()

    body = provider.messages[0]["body"]
    # Bản rút gọn: một câu, không phải nhánh text/plain dài cả chục dòng của email.
    assert len(body.splitlines()) == 1
    assert "Lịch lái thử đã xác nhận" in body


def test_reminder_email_is_personalised(booking_service, booking_db, confirmed_booking_factory):
    """Nhắc lịch dùng chung khung với thư xác nhận, và cá nhân hoá đúng lịch."""
    booking = confirmed_booking_factory(notification_plan_patch={"email_enabled": 1, "sms_enabled": 0})
    with booking_db.transaction(immediate=True) as connection:
        connection.execute(
            "DELETE FROM notification_jobs WHERE booking_id=? AND notification_type='booking_confirmation'",
            (booking["booking_id"],),
        )
        connection.execute(
            "UPDATE notification_jobs SET scheduled_at='2020-01-01T00:00:00Z' WHERE booking_id=?",
            (booking["booking_id"],),
        )
    provider = InMemoryMessagingProvider()
    booking_service.messaging_provider = provider

    booking_service.dispatch_due_notifications()

    html = provider.messages[0]["html_body"]
    assert "ViVi nhắc bạn<br>lịch lái thử" in html
    assert "ViVi nhắc bạn có lịch hẹn với ViVi tại" in html
    assert "Xem thiệp mời của bạn" in html
    assert "/invitation/v1." in html
    # Chung khung với thư xác nhận: cùng bộ ảnh inline, cùng màu vàng, cùng font.
    assert [image.cid for image in provider.messages[0]["inline_images"]] == [
        "vinfast-logo-band",
        "vinfast-logo-band-small",
        "vinfast-bg-base",
        "vinfast-bg-card",
    ]
    assert "#F5C542" in html and "fonts.googleapis.com" not in html
    # Cá nhân hoá: đúng khách, đúng mã lịch của lịch này.
    assert "Huynh Thi Hai Chau" in html
    assert booking["confirmed"]["booking_code"] in html


def test_otp_email_uses_same_shell(booking_service, confirmed_booking_factory):
    """Thư mã xác thực dùng chung khung, và mã nằm trên thanh vàng."""
    from src.services.booking.email_templates import render_otp_email

    mail = render_otp_email(code="482913", expires_in_seconds=300)

    assert "482913" in mail.subject or "482913" in mail.plain_text
    assert "Mã xác thực<br>đặt lịch lái thử" in mail.html
    # Thư này cố ý ĐƠN GIẢN: mã nằm trong một khối riêng, không có thanh trên đầu
    # và không có thanh nav. Nhét cả bố cục thư lịch hẹn vào đây thì mã bị chôn.
    assert 'class="h-code' in mail.html and ">482913<" in mail.html
    # (tên lớp vẫn còn trong khối <style> dùng chung, kiểm phần thân thư mới đúng)
    assert 'class="h-goldbar' not in mail.html
    # MEDIA_BASE_URL lúc chạy test là đường dẫn tương đối, mà email không hiểu
    # đường dẫn tương đối. Khi đó thư phải BỎ HẲN ảnh chìm chứ không được nhét
    # vào một đường dẫn hỏng rồi gửi cho khách một ô ảnh vỡ.
    assert "lac-hong" not in mail.html
    assert [image.cid for image in mail.inline_images] == [
        "vinfast-logo-band",
        "vinfast-logo-band-small",
        "vinfast-bg-base",
        "vinfast-bg-card",
    ]
    assert "không chia sẻ" in mail.plain_text.lower()


def test_vehicle_paragraph_reads_specs_per_variant():
    """Đoạn giới thiệu xe phải đọc thông số của ĐÚNG phiên bản, không đặt cứng.

    Bài này chốt lại một hiểu nhầm từng xảy ra: bản mẫu trong resources/mockups/ để số
    thật nên nhìn vào tưởng thông số bị đặt cứng trong mã. Hai phiên bản khác nhau
    phải cho ra hai đoạn văn khác nhau.
    """
    from src.services.booking.email_templates import _vehicle_paragraph

    vf3 = {
        "model_name": "VF 3", "seat_count": 4, "variant_name": "Eco",
        "battery_capacity_kwh": 18.4, "estimated_range_km": 210.0, "motor_power_kw": 32.0,
    }
    vf9 = {
        "model_name": "VF 9", "seat_count": 7, "variant_name": "Plus",
        "battery_capacity_kwh": 123.0, "estimated_range_km": 580.0, "motor_power_kw": 300.0,
    }
    a, b = _vehicle_paragraph(vf3), _vehicle_paragraph(vf9)

    assert "4 chỗ" in a and "18,4 kWh" in a and "210 km" in a and "32 kW" in a
    assert "7 chỗ" in b and "123 kWh" in b and "580 km" in b and "300 kW" in b
    assert a != b

    # Thông số thiếu thì bỏ hẳn mệnh đề đó, không đoán và không điền số mặc định.
    thieu = {**vf3, "estimated_range_km": None, "motor_power_kw": None, "seat_count": None}
    text = _vehicle_paragraph(thieu)
    assert "210 km" not in text and "32 kW" not in text and "chỗ" not in text
    assert "18,4 kWh" in text


# Hàng dữ liệu dùng cho bài kiểm bên dưới. Mỗi trường một giá trị riêng biệt để
# tìm được trong HTML, không trùng với bất kỳ chữ nào có sẵn trong mẫu thư.
_MARKER_ROW = {
    "booking_code": "MARKCODE",
    "booker_name": "MARKKHACH",
    "driver_name": "MARKKHACH",
    "driver_phone": "MARKSDT",
    "driver_email": "MARKMAIL",
    "model_name": "MARKXE",
    "model_code": "VF8",
    "variant_name": "MARKBAN",
    # Dùng chuỗi chứ không dùng số: số như "222" trùng với giá trị trong CSS của
    # thư nên tìm thấy ở khắp nơi, bài kiểm báo đúng trong khi thật ra sai.
    # _vi_number() trả nguyên xi khi gặp giá trị không phải số nên chỗ này chạy được.
    "estimated_range_km": "MARKKM",
    "motor_power_kw": "MARKKW",
    "battery_capacity_kwh": "MARKPIN",
    "seat_count": "MARKCHO",
    "showroom_name": "MARKSHOWROOM",
    "showroom_address": "MARKDIACHI",
    "showroom_lat": None,
    "showroom_lng": None,
    "start_at": "2026-08-21T02:00:00Z",
    "previous_start_at": "2026-08-19T07:30:00Z",
    "staff_name": "MARKNHANVIEN",
    "staff_phone": "MARKSDTNV",
}

# Trường mọi thư về lịch hẹn đều PHẢI có. Thiếu một cái là khách nhận được thư
# cụt thông tin mà chẳng có gì báo lỗi.
_CORE_FIELDS = (
    "MARKCODE", "MARKKHACH", "MARKSDT", "MARKMAIL",
    "MARKXE", "MARKSHOWROOM", "MARKDIACHI", "MARKNHANVIEN", "MARKSDTNV",
)
# Trường thông số xe, chỉ có ở thư nào còn giữ đoạn giới thiệu xe.
_VEHICLE_FIELDS = ("MARKBAN", "MARKKM", "MARKKW", "MARKPIN", "MARKCHO")


@pytest.mark.parametrize("notification_type", sorted(_BOOKING_COPY))
def test_every_booking_template_carries_the_same_fields(notification_type):
    """Mọi loại thư lịch hẹn phải mang đủ bộ trường như thư xác nhận.

    Bốn loại thư dùng chung một bộ render, nhưng mỗi loại tự chọn hiện khối nào.
    Bài này bắt được trường hợp ai đó tắt nhầm một khối và làm rơi mất thông tin.
    """
    copy = _BOOKING_COPY[notification_type]
    html = render_booking_dark_email(notification_type, dict(_MARKER_ROW)).html

    for field in _CORE_FIELDS:
        assert field in html, f"{notification_type} thiếu trường {field}"

    # Thư nhắc lịch và thư huỷ cố ý bỏ đoạn giới thiệu xe, nên cũng không có
    # thông số. Đó là chủ ý, không phải thiếu sót.
    for field in _VEHICLE_FIELDS:
        assert (field in html) is copy.show_vehicle, (
            f"{notification_type} sai ở trường thông số {field}"
        )

    # Riêng thư đổi giờ có thêm giờ cũ để đối chiếu.
    assert ("Giờ trước đây" in html) is (notification_type == "reschedule_confirmation")
    has_invitation = notification_type in {
        "booking_confirmation",
        "reschedule_confirmation",
        "booking_update",
        "reminder",
        "reminder_24h",
        "reminder_2h",
    }
    assert ("Xem thiệp mời của bạn" in html) is has_invitation
    assert ("/invitation/v1." in html) is has_invitation


def test_lac_hong_watermark_asset_exists():
    """Ảnh chìm của thư mã xác thực phải có thật trong kho ảnh NGUỒN.

    Kiểm ở frontend/src/media/local chứ không kiểm backend/data/media: thư mục
    thứ hai bị gitignore và chỉ sinh ra khi chạy publish_site_media.py, nên trên
    máy cài mới hay trên CI thì nó rỗng. Bài test kiểm thư mục đó sẽ hỏng ở CI
    trong khi mã hoàn toàn đúng.

    Chỉ có bài test này bắt được trường hợp ai đó đổi tên hay xoá file: lúc chạy
    thật thư chỉ lặng lẽ bỏ ảnh chìm chứ không báo lỗi gì.
    """
    from src.services.booking.email_templates import _LAC_HONG_WATERMARK

    source = Path(__file__).resolve().parents[3] / "frontend" / "src" / "media" / "local"
    assert (source / _LAC_HONG_WATERMARK).is_file()
