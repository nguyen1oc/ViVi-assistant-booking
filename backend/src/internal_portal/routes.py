from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.dependencies import internal_portal_service, profile_service
from src.services.llm import summarize_user_profile

from .auth import InternalPrincipal
from .errors import InternalPortalError
from .schemas import (
    BookingAssignmentRequest,
    BookingTransitionRequest,
    InternalUserCreateRequest,
    InternalUserPasswordResetRequest,
    InternalUserUpdateRequest,
    LicenseCheckRequest,
    LoginRequest,
    OperatingHourUpdateRequest,
    ShiftCreateRequest,
    ShiftUpdateRequest,
    ShowroomCreateRequest,
    ShowroomUpdateRequest,
    StaffActionRequest,
    UnavailabilityCreateRequest,
    VehicleModelCreateRequest,
    VehicleModelUpdateRequest,
    VehicleTransferRequest,
    VehicleUnavailabilityCreateRequest,
    VehicleUpdateRequest,
    VehicleVariantCreateRequest,
    VehicleVariantUpdateRequest,
)
from .service import InternalPortalService

router = APIRouter(prefix="/internal", tags=["internal-portal"])
bearer = HTTPBearer(auto_error=False)


def get_internal_portal_service() -> InternalPortalService:
    return internal_portal_service


def _credentials_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    if not credentials or credentials.scheme.casefold() != "bearer":
        raise InternalPortalError("AUTH_REQUIRED", "Cần đăng nhập để tiếp tục.", status_code=401)
    return credentials.credentials


def current_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
) -> InternalPrincipal:
    return service.authenticate(_credentials_token(credentials))


@router.post("/auth/login")
def login(
    request: LoginRequest,
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
):
    return service.login(request.username, request.password)


@router.post("/auth/logout", status_code=204)
def logout(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
) -> None:
    del principal
    service.logout(_credentials_token(credentials))


@router.get("/me")
def me(principal: Annotated[InternalPrincipal, Depends(current_principal)]):
    return principal.as_dict()


@router.get("/users")
def users(
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
    role: str | None = None,
    showroom_id: str | None = None,
    is_active: bool | None = None,
):
    return service.list_internal_users(principal, role=role, showroom_id=showroom_id, is_active=is_active)


@router.post("/users", status_code=201)
def create_user(
    request: InternalUserCreateRequest,
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
):
    return service.create_managed_user(principal, **request.model_dump())


@router.patch("/users/{user_id}")
def update_user(
    user_id: str,
    request: InternalUserUpdateRequest,
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
):
    return service.update_managed_user(
        principal,
        user_id,
        changes=request.model_dump(exclude_unset=True),
    )


@router.post("/users/{user_id}/reset-password")
def reset_user_password(
    user_id: str,
    request: InternalUserPasswordResetRequest,
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
):
    return service.reset_managed_user_password(principal, user_id, password=request.password)


@router.post("/users/{user_id}/revoke-sessions")
def revoke_user_sessions(
    user_id: str,
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
):
    return service.revoke_managed_user_sessions(principal, user_id)


@router.get("/dashboard")
def dashboard(
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
):
    return service.dashboard(principal)


@router.get("/notifications")
def notifications(
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
    unread_only: bool = False,
    limit: int = Query(default=30, ge=1, le=100),
):
    return service.list_notifications(principal, unread_only=unread_only, limit=limit)


@router.post("/notifications/read-all")
def mark_all_notifications_read(
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
):
    return service.mark_all_notifications_read(principal)


@router.post("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
):
    return service.mark_notification_read(principal, notification_id)


@router.get("/bookings")
def bookings(
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
    status: str | None = None,
    showroom_id: str | None = None,
    date: str | None = None,
    staff_id: str | None = None,
    vehicle_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    return service.list_bookings(
        principal,
        status=status,
        showroom_id=showroom_id,
        date=date,
        staff_id=staff_id,
        vehicle_id=vehicle_id,
        limit=limit,
        offset=offset,
    )


@router.get("/showrooms")
def showrooms(
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
):
    return service.list_showrooms(principal)


@router.post("/showrooms", status_code=201)
def create_showroom(
    request: ShowroomCreateRequest,
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
):
    return service.create_showroom(principal, values=request.model_dump())


@router.patch("/showrooms/{showroom_id}")
def update_showroom(
    showroom_id: str,
    request: ShowroomUpdateRequest,
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
):
    return service.update_showroom(principal, showroom_id, changes=request.model_dump(exclude_unset=True))


@router.get("/showrooms/{showroom_id}/operating-hours")
def operating_hours(
    showroom_id: str,
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
):
    return service.list_operating_hours(principal, showroom_id=showroom_id)


@router.put("/showrooms/{showroom_id}/operating-hours/{day_of_week}")
def update_operating_hour(
    showroom_id: str,
    day_of_week: int,
    request: OperatingHourUpdateRequest,
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
):
    if request.day_of_week != day_of_week:
        raise InternalPortalError("DAY_MISMATCH", "Ngày trên URL và nội dung không khớp.")
    return service.update_operating_hour(
        principal,
        showroom_id=showroom_id,
        day_of_week=day_of_week,
        open_time=request.open_time,
        close_time=request.close_time,
        is_closed=request.is_closed,
    )


@router.get("/bookings/{booking_id}")
def booking_detail(
    booking_id: str,
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
):
    return service.get_booking(principal, booking_id)


@router.get("/bookings/{booking_id}/sales-brief.md", response_class=PlainTextResponse)
async def booking_sales_brief(
    booking_id: str,
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
    refresh: bool = False,
) -> PlainTextResponse:
    """Return a scoped cached sales brief, regenerating it only when requested."""
    booking = service.get_booking(principal, booking_id)
    if booking["status"] not in {"confirmed", "cancelled"}:
        raise HTTPException(status_code=409, detail="Sales brief is available only for confirmed or cancelled bookings")
    cached = await asyncio.to_thread(profile_service.booking_profile_summary, booking_id)
    if cached and not refresh:
        return PlainTextResponse(
            cached["summary"],
            media_type="text/markdown; charset=utf-8",
            headers={"X-Profile-Summary-Source": "cache", "X-Profile-Summary-Generated-At": cached["generated_at"]},
        )
    source = await asyncio.to_thread(profile_service.booking_profiles_context, booking_id)
    source["test_drive_context"] = await asyncio.to_thread(profile_service.booking_context_signals, booking_id)
    markdown = await summarize_user_profile(source)
    stored = await asyncio.to_thread(profile_service.save_booking_profile_summary, booking_id, markdown)
    return PlainTextResponse(
        stored["summary"],
        media_type="text/markdown; charset=utf-8",
        headers={"X-Profile-Summary-Source": "generated", "X-Profile-Summary-Generated-At": stored["generated_at"]},
    )


@router.get("/staff")
def staff(
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
    showroom_id: str | None = None,
):
    return service.list_staff(principal, showroom_id=showroom_id)


@router.get("/vehicles")
def vehicles(
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
    showroom_id: str | None = None,
    model_id: str | None = None,
    variant_id: str | None = None,
    operational_status: str | None = None,
):
    return service.list_vehicles(
        principal,
        showroom_id=showroom_id,
        model_id=model_id,
        variant_id=variant_id,
        operational_status=operational_status,
    )


@router.get("/catalog")
def catalog(
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
):
    return service.list_catalog(principal)


@router.post("/catalog/models", status_code=201)
def create_vehicle_model(
    request: VehicleModelCreateRequest,
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
):
    return service.create_vehicle_model(principal, values=request.model_dump())


@router.patch("/catalog/models/{model_id}")
def update_vehicle_model(
    model_id: str,
    request: VehicleModelUpdateRequest,
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
):
    return service.update_vehicle_model(principal, model_id, changes=request.model_dump(exclude_unset=True))


@router.post("/catalog/variants", status_code=201)
def create_vehicle_variant(
    request: VehicleVariantCreateRequest,
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
):
    return service.create_vehicle_variant(principal, values=request.model_dump())


@router.patch("/catalog/variants/{variant_id}")
def update_vehicle_variant(
    variant_id: str,
    request: VehicleVariantUpdateRequest,
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
):
    return service.update_vehicle_variant(principal, variant_id, changes=request.model_dump(exclude_unset=True))


@router.get("/shifts")
def shifts(
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
    showroom_id: str | None = None,
    staff_id: str | None = None,
):
    return service.list_shifts(principal, showroom_id=showroom_id, staff_id=staff_id)


@router.post("/shifts", status_code=201)
def create_shift(
    request: ShiftCreateRequest,
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
):
    return service.create_shift(
        principal,
        staff_id=request.staff_id,
        showroom_id=request.showroom_id,
        start_at=request.start_at.isoformat(),
        end_at=request.end_at.isoformat(),
    )


@router.patch("/shifts/{shift_id}")
def update_shift(
    shift_id: str,
    request: ShiftUpdateRequest,
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
):
    values = request.model_dump(exclude_unset=True)
    return service.update_shift(
        principal,
        shift_id,
        start_at=values["start_at"].isoformat() if values.get("start_at") else None,
        end_at=values["end_at"].isoformat() if values.get("end_at") else None,
        status=values.get("status"),
    )


@router.get("/unavailability")
def unavailability(
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
    showroom_id: str | None = None,
    staff_id: str | None = None,
):
    return service.list_unavailability(principal, showroom_id=showroom_id, staff_id=staff_id)


@router.post("/unavailability", status_code=201)
def create_unavailability(
    request: UnavailabilityCreateRequest,
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
):
    return service.create_unavailability(
        principal,
        staff_id=request.staff_id,
        showroom_id=request.showroom_id,
        start_at=request.start_at.isoformat(),
        end_at=request.end_at.isoformat(),
        reason=request.reason,
    )


@router.patch("/vehicles/{vehicle_id}")
def update_vehicle(
    vehicle_id: str,
    request: VehicleUpdateRequest,
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
):
    return service.update_vehicle(principal, vehicle_id, **request.model_dump())


@router.get("/vehicle-unavailability")
def vehicle_unavailability(
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
    showroom_id: str | None = None,
    vehicle_id: str | None = None,
):
    return service.list_vehicle_unavailability(principal, showroom_id=showroom_id, vehicle_id=vehicle_id)


@router.post("/vehicles/{vehicle_id}/unavailability", status_code=201)
def create_vehicle_unavailability(
    vehicle_id: str,
    request: VehicleUnavailabilityCreateRequest,
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
):
    return service.create_vehicle_unavailability(
        principal,
        vehicle_id,
        start_at=request.start_at.isoformat(),
        end_at=request.end_at.isoformat(),
        reason=request.reason,
    )


@router.delete("/vehicle-unavailability/{record_id}", status_code=204)
def delete_vehicle_unavailability(
    record_id: str,
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
) -> None:
    service.delete_vehicle_unavailability(principal, record_id)


@router.post("/vehicles/{vehicle_id}/transfer", status_code=201)
def transfer_vehicle(
    vehicle_id: str,
    request: VehicleTransferRequest,
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
):
    return service.transfer_vehicle(
        principal,
        vehicle_id,
        to_showroom_id=request.to_showroom_id,
        effective_at=request.effective_at.isoformat(),
    )


@router.get("/vehicle-transfers")
def vehicle_transfers(
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
    limit: int = Query(default=200, ge=1, le=500),
):
    return service.list_vehicle_transfers(principal, limit=limit)


@router.get("/audit-events")
def audit_events(
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
    limit: int = Query(default=100, ge=1, le=500),
):
    return service.list_audit_events(principal, limit=limit)

@router.put("/bookings/{booking_id}/assignment")
def assign_booking(
    booking_id: str,
    request: BookingAssignmentRequest,
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
):
    return service.assign_booking(principal, booking_id, staff_id=request.staff_id)


@router.post("/bookings/{booking_id}/transition")
def transition_booking(
    booking_id: str,
    request: BookingTransitionRequest,
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
):
    return service.transition_booking(principal, booking_id, target_status=request.target_status, note=request.note)


@router.post("/bookings/{booking_id}/license-check")
def record_license_check(
    booking_id: str,
    request: LicenseCheckRequest,
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
):
    return service.record_booking_license_check(
        principal,
        booking_id,
        original_document_presented=request.original_document_presented,
        license_class_matches=request.license_class_matches,
        is_currently_valid=request.is_currently_valid,
        result=request.result,
        rejection_reason=request.rejection_reason,
    )


@router.post("/bookings/{booking_id}/check-in")
def check_in(
    booking_id: str,
    request: StaffActionRequest,
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
):
    return service.transition_booking(
        principal, booking_id, target_status="checked_in", note=request.note
    )


@router.post("/bookings/{booking_id}/complete")
def complete(
    booking_id: str,
    request: StaffActionRequest,
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
):
    return service.transition_booking(
        principal, booking_id, target_status="completed", note=request.note
    )


@router.post("/bookings/{booking_id}/no-show")
def no_show(
    booking_id: str,
    request: StaffActionRequest,
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
):
    return service.transition_booking(
        principal, booking_id, target_status="no_show", note=request.note
    )


@router.post("/bookings/{booking_id}/cancel")
def cancel_booking(
    booking_id: str,
    request: StaffActionRequest,
    principal: Annotated[InternalPrincipal, Depends(current_principal)],
    service: Annotated[InternalPortalService, Depends(get_internal_portal_service)],
):
    return service.transition_booking(
        principal, booking_id, target_status="cancelled", note=request.note
    )
