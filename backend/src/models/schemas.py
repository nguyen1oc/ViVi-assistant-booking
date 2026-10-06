from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

CHAT_MESSAGE_MAX_LENGTH = 150


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=CHAT_MESSAGE_MAX_LENGTH, description="Tin nhắn từ user")
    conversation_id: str = Field(
        default="", max_length=100, description="ID phiên hội thoại (để nhớ lịch sử nhiều lượt)"
    )
    action: Literal[
        "search_options",
        "hold_slot",
        "update_draft",
        "confirm_booking",
        "request_access",
        "verify_access",
        "cancel_booking",
        "reschedule_booking",
    ] | None = Field(
        default=None,
        description="Structured booking action requested by a confirmed UI interaction.",
    )
    action_payload: dict[str, Any] = Field(default_factory=dict)
    context: dict[str, Any] = Field(default_factory=dict)
    # Private bearer token used only by the backend to load a driver's trusted
    # booking context.  Never place it in ``context`` (which reaches the agent).
    driver_invitation_token: str = Field(default="", max_length=512)

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Tin nhắn không được chỉ chứa khoảng trắng.")
        return v


class UiDirective(BaseModel):
    event: str = ""
    phase: str = ""
    allowed_actions: list[str] = Field(default_factory=list)


class FollowUp(BaseModel):
    text: str = Field(min_length=1, max_length=240)


class ChatResponse(BaseModel):
    response: str = Field(..., description="Phản hồi từ agent")
    analysis: str = Field(default="", description="Phân tích nội bộ")
    conversation_id: str = Field(default="", description="ID phiên hội thoại trả về cho client")
    tool_name: str = ""
    tool_input: dict[str, Any] = Field(default_factory=dict)
    action_data: Any | None = None
    action_error: str = ""
    intent: str = ""
    sub_intent: str = ""
    intent_entities: dict[str, Any] = Field(default_factory=dict)
    ui: UiDirective | None = None
    follow_ups: list[FollowUp] = Field(default_factory=list)


class DemoActionRequest(BaseModel):
    action: str = Field(..., min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    conversation_id: str = Field(default="", max_length=100)


class FloatingDemoOptionsRequest(BaseModel):
    vehicle_model: str = Field(..., min_length=1, max_length=120)
    showroom_id: str = Field(default="", max_length=128)
    showroom_query: str = Field(default="", max_length=160)
    showroom_limit: int = Field(default=12, ge=1, le=30)
    latitude: float | None = None
    longitude: float | None = None


class CsvImportRequest(BaseModel):
    csv_text: str = Field(..., min_length=1)


class DatasetImportRequest(BaseModel):
    files: dict[str, str] = Field(..., min_length=1)


class ClientLogRequest(BaseModel):
    level: str = "error"
    message: str = Field(..., min_length=1, max_length=2000)
    context: dict[str, Any] = Field(default_factory=dict)
