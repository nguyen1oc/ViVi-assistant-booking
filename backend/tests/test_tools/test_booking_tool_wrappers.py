import importlib
from unittest.mock import MagicMock

import pytest
from src.agents.tools.get_booking_details.tool import get_booking_details
from src.agents.tools.get_booking_draft.tool import get_booking_draft
from src.agents.tools.request_booking_access.tool import request_booking_access
from src.agents.tools.search_test_drive_options.tool import search_test_drive_options
from src.agents.tools.update_booking_draft.tool import update_booking_draft
from src.agents.tools.verify_booking_access.tool import verify_booking_access

details_module = importlib.import_module("src.agents.tools.get_booking_details.tool")
draft_module = importlib.import_module("src.agents.tools.get_booking_draft.tool")
request_module = importlib.import_module("src.agents.tools.request_booking_access.tool")
search_module = importlib.import_module("src.agents.tools.search_test_drive_options.tool")
update_module = importlib.import_module("src.agents.tools.update_booking_draft.tool")
verify_module = importlib.import_module("src.agents.tools.verify_booking_access.tool")


# test case of Chau + kiểm tra search tool forward đầy đủ bộ lọc xuống booking service
def test_search_test_drive_options_forwards_all_filters(monkeypatch):
    service = MagicMock()
    expected = {"search_stage": "slot_selection", "slots": [{"id": "slot-1"}]}
    service.search_options.return_value = expected
    monkeypatch.setattr(search_module, "booking_service", service)

    result = search_test_drive_options.invoke(
        {
            "vehicle_model": "VF6",
            "vehicle_variant": "Plus",
            "showroom_id": "showroom-q7",
            "showroom_query": "Quận 7",
            "address": "123 Nguyễn Văn Linh, Quận 7",
            "preferred_dates": ["2026-08-10", "2026-08-12"],
            "preferred_date_from": None,
            "preferred_date_to": None,
            "preferred_time": "09:30",
            "latitude": 10.729,
            "longitude": 106.721,
            "limit": 3,
        }
    )

    assert result == expected
    service.search_options.assert_called_once_with(
        vehicle_model="VF6",
        vehicle_variant="Plus",
        showroom_id="showroom-q7",
        showroom_query="Quận 7",
        address="123 Nguyễn Văn Linh, Quận 7",
        preferred_date=None,
        preferred_dates=["2026-08-10", "2026-08-12"],
        preferred_date_from=None,
        preferred_date_to=None,
        preferred_time="09:30",
        latitude=10.729,
        longitude=106.721,
        showroom_limit=5,
        slot_limit=None,
    )


# test case of Chau + kiểm tra search tool dùng đúng default cho tham số tùy chọn
def test_search_test_drive_options_uses_documented_defaults(monkeypatch):
    service = MagicMock()
    service.search_options.return_value = {"search_stage": "showroom_selection"}
    monkeypatch.setattr(search_module, "booking_service", service)

    search_test_drive_options.invoke({"vehicle_model": "VF8"})

    service.search_options.assert_called_once_with(
        vehicle_model="VF8",
        vehicle_variant=None,
        showroom_id=None,
        showroom_query=None,
        address=None,
        preferred_date=None,
        preferred_dates=None,
        preferred_date_from=None,
        preferred_date_to=None,
        preferred_time=None,
        latitude=None,
        longitude=None,
        showroom_limit=5,
        slot_limit=None,
    )


# test case of Chau + kiểm tra get draft tool chỉ forward booking id
def test_get_booking_draft_forwards_booking_id(monkeypatch):
    service = MagicMock()
    service.get_booking_draft.return_value = {"id": "booking-1", "status": "held"}
    monkeypatch.setattr(draft_module, "booking_service", service)

    result = get_booking_draft.invoke({"booking_id": "booking-1"})

    assert result["status"] == "held"
    service.get_booking_draft.assert_called_once_with("booking-1")


# test case of Chau + kiểm tra update draft tool forward person notification và version patch
def test_update_booking_draft_forwards_non_license_patches(monkeypatch):
    service = MagicMock()
    service.update_booking_draft.return_value = {"id": "booking-1", "version": 3}
    monkeypatch.setattr(update_module, "booking_service", service)
    booker = {"full_name": "Chau", "phone": "0901234567"}
    driver = {"full_name": "Nam", "phone": "0912345678"}
    notifications = {"sms_enabled": 1, "email_enabled": 0}

    result = update_booking_draft.invoke(
        {
            "booking_id": "booking-1",
            "booker_patch": booker,
            "driver_patch": driver,
            "driver_same_as_booker": False,
            "notification_plan_patch": notifications,
            "expected_version": 2,
        }
    )

    assert result["version"] == 3
    service.update_booking_draft.assert_called_once_with(
        "booking-1",
        booker_patch=booker,
        driver_patch=driver,
        driver_same_as_booker=False,
        license_patch=None,
        notification_plan_patch=notifications,
        expected_version=2,
    )


# test case of Chau + kiểm tra cam kết GPLX đi xuyên suốt từ tool vào service và draft thật
def test_update_booking_draft_tool_persists_license_commitment(
    monkeypatch, booking_service, catalog
):
    held = booking_service.hold_slot(catalog["slot_main"], "hold:tool-license-integration")
    monkeypatch.setattr(update_module, "booking_service", booking_service)

    result = update_booking_draft.invoke(
        {
            "booking_id": held["booking_id"],
            "booker_patch": {
                "full_name": "Huynh Thi Hai Chau",
                "phone": "0901234567",
                "email": "chau@example.com",
            },
            "driver_same_as_booker": True,
            "has_valid_license_commitment": True,
            "expected_version": 1,
        }
    )

    assert result["license_declaration"]["has_driving_license"] is True
    assert "license.has_driving_license" not in result["missing_required_fields"]
    assert result["is_ready_to_confirm"] is True


# test case of Chau + kiểm tra request access tool forward purpose channel và không bật expose OTP
def test_request_booking_access_forwards_safe_arguments(monkeypatch):
    service = MagicMock()
    service.request_access.return_value = {
        "challenge_id": "otp-1",
        "destination_masked": "*******567",
    }
    monkeypatch.setattr(request_module, "booking_service", service)

    result = request_booking_access.invoke(
        {
            "booking_code": "VF260804ABC123",
            "contact_value": "0901234567",
            "purpose": "lookup",
            "preferred_channel": "email",
        }
    )

    assert "otp_code" not in result
    service.request_access.assert_called_once_with(
        booking_code="VF260804ABC123",
        contact_value="0901234567",
        purpose="lookup",
        preferred_channel="email",
    )


# test case of Chau + kiểm tra verify access tool forward challenge và OTP xuống service
def test_verify_booking_access_forwards_challenge_and_code(monkeypatch):
    service = MagicMock()
    service.verify_access.return_value = {"access_session_token": "token-1", "booking_id": "booking-1"}
    monkeypatch.setattr(verify_module, "booking_service", service)

    result = verify_booking_access.invoke({"challenge_id": "otp-1", "otp_code": "123456"})

    assert result["booking_id"] == "booking-1"
    service.verify_access.assert_called_once_with("otp-1", "123456")


# test case of Chau + kiểm tra get details tool forward token và một trong hai booking identifier
@pytest.mark.parametrize(
    ("booking_id", "booking_code"),
    [("booking-1", None), (None, "VF260804ABC123")],
)
def test_get_booking_details_forwards_access_scope(monkeypatch, booking_id, booking_code):
    service = MagicMock()
    service.get_booking_details.return_value = {"status": "confirmed"}
    monkeypatch.setattr(details_module, "booking_service", service)

    result = get_booking_details.invoke(
        {
            "access_session_token": "token-1",
            "booking_id": booking_id,
            "booking_code": booking_code,
        }
    )

    assert result["status"] == "confirmed"
    service.get_booking_details.assert_called_once_with(
        "token-1",
        booking_id=booking_id,
        booking_code=booking_code,
    )
