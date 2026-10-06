from langchain_core.tools import tool

from src.dependencies import booking_service
from src.observability import trace_backend_operation


@tool
@trace_backend_operation("BookingService.search_options")
def search_test_drive_options(
    vehicle_model: str,
    vehicle_variant: str | None = None,
    showroom_id: str | int | None = None,
    showroom_query: str | None = None,
    address: str | None = None,
    preferred_date: str | None = None,
    preferred_dates: list[str] | None = None,
    preferred_date_from: str | None = None,
    preferred_date_to: str | None = None,
    preferred_time: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    showroom_limit: int = 5,
    slot_limit: int | None = None,
) -> dict:
    """Tìm showroom hoặc slot lái thử; không giữ slot."""
    str_showroom_id = str(showroom_id) if showroom_id is not None else None
    return booking_service.search_options(
        vehicle_model=vehicle_model,
        vehicle_variant=vehicle_variant,
        showroom_id=str_showroom_id,
        showroom_query=showroom_query,
        address=address,
        preferred_date=preferred_date,
        preferred_dates=preferred_dates,
        preferred_date_from=preferred_date_from,
        preferred_date_to=preferred_date_to,
        preferred_time=preferred_time,
        latitude=latitude,
        longitude=longitude,
        showroom_limit=showroom_limit,
        slot_limit=slot_limit,
    )
