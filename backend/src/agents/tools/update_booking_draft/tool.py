from langchain_core.tools import tool

from src.dependencies import booking_service
from src.observability import trace_backend_operation


@tool
@trace_backend_operation("BookingService.update_booking_draft")
def update_booking_draft(
    booking_id: str,
    booker_patch: dict | None = None,
    driver_patch: dict | None = None,
    driver_same_as_booker: bool = False,
    has_valid_license_commitment: bool | None = None,
    notification_plan_patch: dict | None = None,
    expected_version: int | None = None,
) -> dict:
    """Patch booking held với optimistic concurrency; không đổi slot hoặc chốt lịch.

    Args:
        booking_id: ID của booking draft đang held.
        booker_patch: Thông tin liên lạc của người đặt lịch.
        driver_patch: Thông tin của người lái (nếu khác người đặt).
        driver_same_as_booker: True nếu người lái cũng là người đặt.
        has_valid_license_commitment: True nếu người lái xác nhận có GPLX hợp lệ,
            False nếu không có. None nếu chưa xác nhận.
        notification_plan_patch: Kênh nhận thông báo (SMS, Email, Zalo).
        expected_version: Version token để tránh dirty write conflicts.
    """
    license_patch = None
    if has_valid_license_commitment is not None:
        license_patch = {"has_driving_license": has_valid_license_commitment}

    return booking_service.update_booking_draft(
        booking_id,
        booker_patch=booker_patch,
        driver_patch=driver_patch,
        driver_same_as_booker=driver_same_as_booker,
        license_patch=license_patch,
        notification_plan_patch=notification_plan_patch,
        expected_version=expected_version,
    )
