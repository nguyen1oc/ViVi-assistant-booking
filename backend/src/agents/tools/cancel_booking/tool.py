from langchain_core.tools import tool

from src.dependencies import booking_service


@tool
def cancel_booking(
    booking_id: str,
    access_session_token: str,
    ui_action_id: str,
    reason: str | None = None,
) -> dict:
    """Hủy booking đã xác nhận sau khi người dùng đã xác thực và xác nhận thao tác trên UI."""
    return booking_service.cancel_booking(
        booking_id,
        access_session_token,
        ui_action_id,
        reason,
    )
