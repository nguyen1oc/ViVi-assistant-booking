from langchain_core.tools import tool

from src.dependencies import booking_service
from src.observability import trace_backend_operation


@tool
@trace_backend_operation("BookingService.hold_slot")
def hold_test_drive_slot(slot_id: str, ui_action_id: str) -> dict:
    """Giữ slot lái thử trong 5 phút. Gọi tool này ngay khi người dùng chọn hoặc yêu cầu đặt một khung giờ cụ thể trong đoạn chat."""
    return booking_service.hold_slot(slot_id, ui_action_id)
