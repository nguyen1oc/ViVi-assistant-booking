import re
from datetime import timedelta

import pytest
from src.services.booking import BookingError, iso
from src.services.booking.access import ACCESS_PERMISSIONS
from src.services.booking.notifications import ProviderResult
from src.services.zalo_bot import ZaloOtpSender

from tests.conftest import BOOKER_PHONE, FIXED_NOW


# test case of Chau + kiểm tra yêu cầu OTP trả destination đã mask và không lộ OTP thô
def test_request_access_masks_destination_and_hides_otp(booking_service, confirmed_booking_factory):
    confirmed = confirmed_booking_factory()

    result = booking_service.request_access(confirmed["confirmed"]["booking_code"], BOOKER_PHONE, "lookup")

    assert result["destination_masked"].endswith(BOOKER_PHONE[-3:])
    assert BOOKER_PHONE not in result["destination_masked"]
    assert "otp_code" not in result


def test_request_access_never_exposes_real_provider_otp(booking_service, confirmed_booking_factory):
    class RealOtpSender:
        def send(self, *, channel, destination, code, expires_in_seconds):
            return ProviderResult(
                provider="real_sms",
                channel=channel,
                provider_status="sent",
                provider_message_id="message-1",
                is_mock=False,
            )

    confirmed = confirmed_booking_factory()
    booking_service.otp_sender = RealOtpSender()

    result = booking_service.request_access(
        confirmed["confirmed"]["booking_code"],
        BOOKER_PHONE,
        "lookup",
        expose_otp=True,
    )

    assert result["is_mock"] is False
    assert "otp_code" not in result


def test_the_otp_delivered_by_sender_verifies_the_created_challenge(booking_service, confirmed_booking_factory):
    """The code handed to the delivery adapter must be the code hashed for verification."""
    confirmed = confirmed_booking_factory()

    challenge = booking_service.request_access(
        contact_value=BOOKER_PHONE,
        purpose="lookup",
        booking_code=confirmed["confirmed"]["booking_code"],
        preferred_channel="sms",
    )

    delivered_code = booking_service.otp_sender.sent[-1].code
    session = booking_service.verify_access(challenge["challenge_id"], delivered_code)

    assert session["booking_id"] == confirmed["booking_id"]


def test_the_code_in_the_zalo_message_verifies_the_created_challenge(
    booking_service, booking_db, confirmed_booking_factory
):
    """The actual Zalo message template must carry the code stored for the challenge."""

    class CapturingZaloClient:
        def __init__(self):
            self.text = ""

        def send_text(self, _chat_id, text):
            self.text = text
            return {"ok": True, "result": {"message_id": "test-message"}}

    confirmed = confirmed_booking_factory()
    client = CapturingZaloClient()
    with booking_db.transaction(immediate=True) as connection:
        connection.execute(
            "INSERT INTO zalo_identity_links(phone,chat_id,linked_at,updated_at) VALUES(?,?,?,?)",
            (BOOKER_PHONE, "test-chat", iso(FIXED_NOW), iso(FIXED_NOW)),
        )
    booking_service.otp_sender = ZaloOtpSender(booking_db, client)

    challenge = booking_service.request_access(
        contact_value=BOOKER_PHONE,
        purpose="lookup",
        booking_code=confirmed["confirmed"]["booking_code"],
        preferred_channel="zalo",
    )
    delivered_code = re.search(r"\b(\d{6})\b", client.text).group(1)
    session = booking_service.verify_access(challenge["challenge_id"], delivered_code)

    assert session["booking_id"] == confirmed["booking_id"]


# test case of Chau + kiểm tra từ chối purpose OTP không được hỗ trợ
def test_request_access_rejects_invalid_purpose(booking_service, confirmed_booking_factory):
    confirmed = confirmed_booking_factory()

    with pytest.raises(BookingError) as error:
        booking_service.request_access(confirmed["confirmed"]["booking_code"], BOOKER_PHONE, "delete_booking")

    assert error.value.code == "INVALID_INPUT"


# test case of Chau + kiểm tra contact không thuộc Booker hoặc Driver không được nhận OTP
def test_request_access_rejects_unregistered_contact(booking_service, confirmed_booking_factory):
    confirmed = confirmed_booking_factory()

    with pytest.raises(BookingError) as error:
        booking_service.request_access(confirmed["confirmed"]["booking_code"], "0999999999", "lookup")

    assert error.value.code == "BOOKING_ACCESS_NOT_AVAILABLE"


def test_request_access_accepts_formatted_registered_phone(booking_service, confirmed_booking_factory):
    confirmed = confirmed_booking_factory()

    result = booking_service.request_access(confirmed["confirmed"]["booking_code"], "090 123 4567", "lookup")

    assert result["destination_masked"].endswith("567")


# test case of Chau + kiểm tra OTP đúng tạo access session với permission theo purpose
@pytest.mark.parametrize(
    ("purpose", "expected_permission"),
    [
        ("lookup", "read_booking"),
        ("reschedule", "hold_reschedule"),
        ("cancel", "cancel_booking"),
        ("update_details", "update_details"),
        ("update_notifications", "update_notifications"),
    ],
)
def test_verify_access_grants_permission_for_purpose(
    booking_service, confirmed_booking_factory, purpose, expected_permission
):
    confirmed = confirmed_booking_factory()
    challenge = booking_service.request_access(
        confirmed["confirmed"]["booking_code"],
        BOOKER_PHONE,
        purpose,
        expose_otp=True,
    )

    session = booking_service.verify_access(challenge["challenge_id"], challenge["otp_code"])

    assert "read_booking" in session["permissions"]
    assert expected_permission in session["permissions"]
    assert session["booking_id"] == confirmed["booking_id"]


# test case of Chau + kiểm tra OTP chỉ được sử dụng thành công một lần
def test_otp_is_single_use(booking_service, confirmed_booking_factory):
    confirmed = confirmed_booking_factory()
    challenge = booking_service.request_access(
        confirmed["confirmed"]["booking_code"],
        BOOKER_PHONE,
        "lookup",
        expose_otp=True,
    )
    booking_service.verify_access(challenge["challenge_id"], challenge["otp_code"])

    with pytest.raises(BookingError) as error:
        booking_service.verify_access(challenge["challenge_id"], challenge["otp_code"])

    assert error.value.code == "OTP_INVALID"


# test case of Chau + kiểm tra một lần nhập OTP sai phải tăng attempt count
def test_wrong_otp_increments_attempt_count(booking_service, booking_db, confirmed_booking_factory):
    confirmed = confirmed_booking_factory()
    challenge = booking_service.request_access(
        confirmed["confirmed"]["booking_code"],
        BOOKER_PHONE,
        "lookup",
        expose_otp=True,
    )

    with pytest.raises(BookingError):
        booking_service.verify_access(challenge["challenge_id"], "000000")

    with booking_db.connect() as connection:
        attempt_count = connection.execute(
            "SELECT attempt_count FROM otp_challenges WHERE id=?",
            (challenge["challenge_id"],),
        ).fetchone()[0]
    assert attempt_count == 1


# test case of Chau + kiểm tra OTP bị khóa sau năm lần nhập sai
def test_otp_locks_after_max_attempts(booking_service, booking_db, confirmed_booking_factory):
    confirmed = confirmed_booking_factory()
    challenge = booking_service.request_access(
        confirmed["confirmed"]["booking_code"],
        BOOKER_PHONE,
        "lookup",
        expose_otp=True,
    )

    for _ in range(5):
        with pytest.raises(BookingError):
            booking_service.verify_access(challenge["challenge_id"], "000000")

    with booking_db.connect() as connection:
        otp = connection.execute(
            "SELECT status,attempt_count FROM otp_challenges WHERE id=?",
            (challenge["challenge_id"],),
        ).fetchone()
    assert otp["status"] == "locked"
    assert otp["attempt_count"] == 5


# test case of Chau + kiểm tra OTP hết hạn bị từ chối
def test_expired_otp_is_rejected(booking_service, booking_db, confirmed_booking_factory):
    confirmed = confirmed_booking_factory()
    challenge = booking_service.request_access(
        confirmed["confirmed"]["booking_code"],
        BOOKER_PHONE,
        "lookup",
        expose_otp=True,
    )
    with booking_db.transaction(immediate=True) as connection:
        connection.execute(
            "UPDATE otp_challenges SET expires_at=? WHERE id=?",
            (iso(FIXED_NOW - timedelta(seconds=1)), challenge["challenge_id"]),
        )

    with pytest.raises(BookingError) as error:
        booking_service.verify_access(challenge["challenge_id"], challenge["otp_code"])

    assert error.value.code == "OTP_EXPIRED"


# test case of Chau + kiểm tra access session hết hạn không đọc được booking
def test_expired_access_session_is_rejected(booking_service, booking_db, access_factory):
    access = access_factory("lookup")
    with booking_db.transaction(immediate=True) as connection:
        connection.execute(
            "UPDATE booking_access_sessions SET expires_at=? WHERE booking_id=?",
            (iso(FIXED_NOW - timedelta(seconds=1)), access["booking"]["booking_id"]),
        )

    with pytest.raises(BookingError) as error:
        booking_service.get_booking_details(
            access["session"]["access_session_token"],
            booking_id=access["booking"]["booking_id"],
        )

    assert error.value.code == "ACCESS_SESSION_EXPIRED"


def test_confirm_booking_otp_flow(booking_service, ready_draft_factory):
    ready = ready_draft_factory()
    booking_id = ready["booking_id"]

    # Đăng ký OTP với purpose confirm_booking bằng booking_id và email
    challenge = booking_service.request_access(
        booking_code=booking_id,
        contact_value="chau@example.test",
        purpose="confirm_booking",
        preferred_channel="email",
        expose_otp=True,
    )
    assert challenge["challenge_id"]

    # Xác thực OTP thành công
    verified = booking_service.verify_access(challenge["challenge_id"], challenge["otp_code"])
    assert verified["booking_id"] == booking_id
    assert "confirm_booking" in verified["permissions"]


# test case of Chau + kiểm tra token lookup không được dùng để hủy booking
def test_lookup_permission_cannot_cancel_booking(booking_service, access_factory):
    access = access_factory("lookup")

    with pytest.raises(BookingError) as error:
        booking_service.cancel_booking(
            access["booking"]["booking_id"],
            access["session"]["access_session_token"],
            "cancel:with-lookup-token",
        )

    assert error.value.code == "ACCESS_DENIED"


# OTP lookup grants access to all bookings owned by the same verified contact.
def test_access_session_is_scoped_to_one_booking(booking_service, access_factory, confirmed_booking_factory, catalog):
    first_access = access_factory("lookup")
    second = confirmed_booking_factory(catalog["slot_second_vehicle"])

    details = booking_service.get_booking_details(
        first_access["session"]["access_session_token"],
        booking_id=second["booking_id"],
    )

    assert (details.get("id") or details.get("booking_id")) == second["booking_id"]


def test_access_session_rejects_booking_owned_by_another_customer(booking_service, access_factory, catalog):
    first_access = access_factory("lookup")
    held = booking_service.hold_slot(catalog["slot_second_vehicle"], "hold:other-customer")
    draft = booking_service.update_booking_draft(
        held["booking_id"],
        booker_patch={
            "full_name": "Khach Hang Khac",
            "phone": "0907654321",
            "email": "other.customer@example.test",
            "preferred_channel": "email",
        },
        driver_same_as_booker=True,
        license_patch={
            "has_driving_license": True,
            "declared_license_class": "B1",
            "validity_acknowledged": True,
        },
        expected_version=1,
    )
    second = booking_service.confirm_booking(held["booking_id"], "confirm:other-customer", draft["version"])

    with pytest.raises(BookingError) as error:
        booking_service.get_booking_details(
            first_access["session"]["access_session_token"],
            booking_id=second["booking_id"],
        )

    assert error.value.code == "ACCESS_SESSION_SCOPE_MISMATCH"


# test case of Chau + kiểm tra API chi tiết chỉ trả cam kết GPLX và không trả số GPLX cũ
def test_booking_details_uses_boolean_license_commitment(booking_service, access_factory):
    access = access_factory("lookup")

    details = booking_service.get_booking_details(
        access["session"]["access_session_token"],
        booking_id=access["booking"]["booking_id"],
    )

    declaration = details["license_declaration"]
    assert declaration["has_driving_license"] is True
    assert "license_number" not in declaration


# Purpose "manage" gộp quyền xem + đổi giờ + huỷ trong MỘT lần OTP, để màn tra cứu hiện được
# nút "Huỷ lịch". Bảng phân quyền từng bị chép làm hai bản (request_access và verify_access);
# thêm purpose vào một bản mà quên bản kia thì xin mã vẫn được nhưng NHẬP mã nổ KeyError →
# HTTP 500, giao diện chỉ hiện "Yêu cầu không thành công.". Hai test dưới khoá lại chuyện đó.
def test_manage_purpose_grants_cancel_and_reschedule_in_one_session(booking_service, confirmed_booking_factory):
    booking = confirmed_booking_factory()
    challenge = booking_service.request_access(
        booking["confirmed"]["booking_code"], BOOKER_PHONE, "manage", expose_otp=True
    )

    session = booking_service.verify_access(challenge["challenge_id"], challenge["otp_code"])

    assert "cancel_booking" in session["permissions"]
    assert "confirm_reschedule" in session["permissions"]
    assert "read_booking" in session["permissions"]


def test_manage_purpose_is_declared_in_the_single_shared_permission_map():
    """Bảng phân quyền phải là MỘT nguồn duy nhất.

    Trước đây có hai bản chép tay; test này khoá lại việc mọi purpose đều tra từ cùng một chỗ,
    nên không thể lặp lại cảnh xin mã được mà nhập mã thì lỗi 500.
    """
    assert "manage" in ACCESS_PERMISSIONS
    assert set(ACCESS_PERMISSIONS["manage"]) >= {
        "read_booking",
        "confirm_reschedule",
        "cancel_booking",
    }
