from langchain_core.tools import tool

from src.dependencies import booking_service


@tool
def reschedule_booking(
    current_booking_id: str,
    new_slot_id: str,
    access_session_token: str,
    ui_action_id: str,
) -> dict:
    """Đổi booking đã xác nhận sang slot mới sau khi người dùng xác thực và xác nhận trên UI."""
    return booking_service.reschedule_booking(
        current_booking_id,
        new_slot_id,
        access_session_token,
        ui_action_id,
    )
