from langchain_core.tools import tool

from src.dependencies import booking_service
from src.observability import trace_backend_operation


@tool
@trace_backend_operation("BookingService.confirm_booking")
def confirm_test_drive_booking(booking_id: str, expected_version: int, ui_action_id: str) -> dict:
    """Chốt booking và tạo mã đặt lịch chính thức. Gọi tool này ngay khi người dùng yêu cầu chốt hoặc xác nhận đặt lịch trong đoạn chat."""
    return booking_service.confirm_booking(booking_id, ui_action_id, expected_version)
