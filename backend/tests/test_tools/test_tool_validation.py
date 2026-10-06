import importlib
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError
from src.agents.tools.search_test_drive_options.tool import search_test_drive_options
from src.agents.tools.update_booking_draft.tool import update_booking_draft

search_module = importlib.import_module("src.agents.tools.search_test_drive_options.tool")
update_module = importlib.import_module("src.agents.tools.update_booking_draft.tool")


# test case of Chau + kiểm tra search tool bắt buộc có vehicle_model trước khi gọi service
def test_search_tool_rejects_missing_required_vehicle_model(monkeypatch):
    service = MagicMock()
    monkeypatch.setattr(search_module, "booking_service", service)

    with pytest.raises(ValidationError):
        search_test_drive_options.invoke({"limit": 5})

    service.search_options.assert_not_called()


@pytest.mark.parametrize(
    "invalid_patch",
    [
        {"vehicle_model": "VF8", "showroom_limit": "many"},
        {"vehicle_model": "VF8", "latitude": "north"},
        {"vehicle_model": "VF8", "longitude": "east"},
    ],
)
# test case of Chau + kiểm tra search tool chặn kiểu dữ liệu số sai trước service boundary
def test_search_tool_rejects_invalid_numeric_types(monkeypatch, invalid_patch):
    service = MagicMock()
    monkeypatch.setattr(search_module, "booking_service", service)

    with pytest.raises(ValidationError):
        search_test_drive_options.invoke(invalid_patch)

    service.search_options.assert_not_called()


# test case of Chau + kiểm tra update tool chặn patch người đặt sai kiểu list thay vì dict
def test_update_tool_rejects_non_mapping_booker_patch(monkeypatch):
    service = MagicMock()
    monkeypatch.setattr(update_module, "booking_service", service)

    with pytest.raises(ValidationError):
        update_booking_draft.invoke({"booking_id": "booking-1", "booker_patch": ["name", "phone"]})

    service.update_booking_draft.assert_not_called()
