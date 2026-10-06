from langchain_core.tools import tool

from src.dependencies import booking_service
from src.observability import trace_backend_operation


@tool
@trace_backend_operation("BookingService.request_access")
def request_booking_access(booking_code: str | None = None, contact_value: str = "", purpose: str = "lookup", preferred_channel: str = "email") -> dict:
    """Open email access UI when contact is missing; otherwise create and send a booking OTP."""
    normalized_contact = contact_value.strip()
    if not normalized_contact:
        return {
            "requires_contact_value": True,
            "contact_type": "email",
            "purpose": purpose,
            "suggested_next_action": "show_booking_access_email_form",
        }
    return booking_service.request_access(
        contact_value=normalized_contact,
        purpose=purpose,
        booking_code=booking_code,
        preferred_channel="email",
    )
