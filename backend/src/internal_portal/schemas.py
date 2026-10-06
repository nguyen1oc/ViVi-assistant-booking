from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)


class InternalUserCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=256)
    display_name: str = Field(min_length=1, max_length=120)
    role: Literal["staff", "showroom_manager", "operations_admin"]
    staff_id: str | None = Field(default=None, max_length=120)
    showroom_ids: list[str] = Field(default_factory=list, max_length=50)


class InternalUserUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    role: Literal["staff", "showroom_manager", "operations_admin"] | None = None
    staff_id: str | None = Field(default=None, max_length=120)
    showroom_ids: list[str] | None = Field(default=None, max_length=50)
    is_active: bool | None = None


class InternalUserPasswordResetRequest(BaseModel):
    password: str = Field(min_length=8, max_length=256)


class LicenseCheckRequest(BaseModel):
    ui_action_id: str = Field(min_length=8, max_length=160)
    original_document_presented: bool
    license_class_matches: bool
    is_currently_valid: bool
    result: Literal["verified", "rejected"]
    rejection_reason: str | None = Field(default=None, max_length=500)


class StaffActionRequest(BaseModel):
    ui_action_id: str = Field(min_length=8, max_length=160)
    note: str | None = Field(default=None, max_length=500)


class BookingAssignmentRequest(BaseModel):
    staff_id: str = Field(min_length=1, max_length=120)


class BookingTransitionRequest(BaseModel):
    target_status: Literal["checked_in", "completed", "no_show", "cancelled"]
    note: str | None = Field(default=None, max_length=500)


class ShiftCreateRequest(BaseModel):
    staff_id: str = Field(min_length=1, max_length=120)
    showroom_id: str = Field(min_length=1, max_length=120)
    start_at: datetime
    end_at: datetime


class UnavailabilityCreateRequest(ShiftCreateRequest):
    reason: str = Field(min_length=2, max_length=500)


class ShiftUpdateRequest(BaseModel):
    start_at: datetime | None = None
    end_at: datetime | None = None
    status: Literal["scheduled", "cancelled"] | None = None


class OperatingHourUpdateRequest(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    open_time: str | None = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    close_time: str | None = Field(default=None, pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    is_closed: bool = False


class VehicleUpdateRequest(BaseModel):
    operational_status: Literal["available", "in_use", "charging", "maintenance", "out_of_service"] | None = None
    battery_soc: float | None = Field(default=None, ge=0, le=100)
    charging_status: Literal["not_charging", "charging", "fully_charged", "unknown"] | None = None


class VehicleTransferRequest(BaseModel):
    to_showroom_id: str = Field(min_length=1, max_length=120)
    effective_at: datetime


class VehicleUnavailabilityCreateRequest(BaseModel):
    start_at: datetime
    end_at: datetime
    reason: str = Field(min_length=2, max_length=500)


class ShowroomCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=160)
    address: str = Field(min_length=1, max_length=500)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    phone: str | None = Field(default=None, max_length=80)
    email: str | None = Field(default=None, max_length=160)
    timezone: str = Field(default="Asia/Ho_Chi_Minh", min_length=1, max_length=80)
    region: str | None = Field(default=None, max_length=80)
    map_visible: bool = True
    is_active: bool = True


class ShowroomUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    address: str | None = Field(default=None, min_length=1, max_length=500)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    phone: str | None = Field(default=None, max_length=80)
    email: str | None = Field(default=None, max_length=160)
    timezone: str | None = Field(default=None, min_length=1, max_length=80)
    region: str | None = Field(default=None, max_length=80)
    map_visible: bool | None = None
    is_active: bool | None = None


class VehicleModelCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=160)
    vehicle_type: str = Field(min_length=1, max_length=80)
    required_license_class: str | None = Field(default=None, max_length=40)
    license_requirement_note: str | None = Field(default=None, max_length=500)
    seat_count: int | None = Field(default=None, ge=1, le=100)
    test_drive_eligible: bool = True
    is_active: bool = True


class VehicleModelUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    vehicle_type: str | None = Field(default=None, min_length=1, max_length=80)
    required_license_class: str | None = Field(default=None, max_length=40)
    license_requirement_note: str | None = Field(default=None, max_length=500)
    seat_count: int | None = Field(default=None, ge=1, le=100)
    test_drive_eligible: bool | None = None
    is_active: bool | None = None


class VehicleVariantCreateRequest(BaseModel):
    model_id: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=160)
    battery_capacity_kwh: float | None = Field(default=None, ge=0)
    estimated_range_km: float | None = Field(default=None, ge=0)
    motor_power_kw: float | None = Field(default=None, ge=0)
    default_test_drive_minutes: int | None = Field(default=None, ge=5, le=480)
    is_active: bool = True


class VehicleVariantUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    battery_capacity_kwh: float | None = Field(default=None, ge=0)
    estimated_range_km: float | None = Field(default=None, ge=0)
    motor_power_kw: float | None = Field(default=None, ge=0)
    default_test_drive_minutes: int | None = Field(default=None, ge=5, le=480)
    is_active: bool | None = None
