from langchain_core.tools import tool

from src.dependencies import booking_service
from src.observability import trace_backend_operation


@tool
@trace_backend_operation("BookingService.get_booking_details")
def get_booking_details(
    access_session_token: str, booking_id: str | None = None, booking_code: str | None = None
) -> dict:
    """Đọc booking đã tồn tại sau khi xác minh OTP."""
    return booking_service.get_booking_details(access_session_token, booking_id=booking_id, booking_code=booking_code)
