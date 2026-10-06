from langchain_core.tools import tool

from src.dependencies import booking_service
from src.observability import trace_backend_operation


@tool
@trace_backend_operation("BookingService.get_booking_draft")
def get_booking_draft(booking_id: str) -> dict:
    """Đọc booking held, field còn thiếu và TTL; không xác nhận booking."""
    return booking_service.get_booking_draft(booking_id)
