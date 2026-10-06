from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from src.services.profile.taxonomy import (
    BOOKING_SIGNAL_SPECS,
    PROFILE_SIGNAL_SPECS,
    SignalCategory,
    booking_key_schema_description,
    canonical_profile_key,
    normalize_key,
    profile_key_schema_description,
)

MULTI_VALUE_PROFILE_KEYS = frozenset({
    "primary_use",
    "vehicle_interest",
    "feature_interest",
    "policy_interest",
    "test_drive_priority",
    "current_vehicle_pain_points",
})


class SignalCandidate(BaseModel):
    category: SignalCategory = Field(description="One of the canonical signal categories.")
    key: str = Field(description=profile_key_schema_description())
    value: Any = Field(description="Value matching the key contract in the tool description.")
    description: str = Field(default="", description="Human-readable evidence; required for custom.* keys.")
    certainty: Literal["known", "likely", "possible"] = "possible"
    confidence: float = Field(default=0.5, ge=0, le=1)
    source_type: Literal["explicit_user", "implicit_user", "trusted_domain"] = "implicit_user"
    operation: Literal["add", "strengthen", "weaken", "revise", "retract"] = "add"


class ProfileSignalCandidate(SignalCandidate):
    subject: Literal["self", "third_party"] = "self"

    @model_validator(mode="after")
    def validate_profile_contract(self) -> ProfileSignalCandidate:
        self.key = canonical_profile_key(self.key)
        spec = PROFILE_SIGNAL_SPECS.get(self.key)
        if spec is None:
            if not self.key.startswith("custom."):
                raise ValueError("profile signal key must be registered or start with custom.")
            if not self.description.strip():
                raise ValueError("custom profile signal requires a description")
            return self
        if self.category != spec["category"]:
            raise ValueError(f"{self.key} must use category={spec['category']}")
        if self.key == "household_size" and (not isinstance(self.value, int) or isinstance(self.value, bool) or self.value < 1):
            raise ValueError("household_size must be an integer >= 1")
        if self.key == "commute_distance_km" and (not isinstance(self.value, (int, float)) or isinstance(self.value, bool) or self.value < 0):
            raise ValueError("commute_distance_km must be a number >= 0")
        # These dimensions can have more than one value. Keep the write contract
        # backward-compatible with callers still sending one string, without
        # enforcing the taxonomy's recommended value catalog.
        if self.key in MULTI_VALUE_PROFILE_KEYS and isinstance(self.value, str):
            self.value = [self.value]
        if self.key == "policy_interest":
            if not isinstance(self.value, list):
                raise ValueError("policy_interest must be a list of policy topic/model objects")
            normalized: list[dict[str, str]] = []
            for item in self.value:
                if not isinstance(item, dict):
                    raise ValueError("each policy_interest item must be an object")
                topic = str(item.get("topic") or "").strip()
                vehicle_model = str(item.get("vehicle_model") or "").strip()
                if not topic or not vehicle_model:
                    raise ValueError("each policy_interest item requires topic and vehicle_model")
                normalized.append({"topic": topic, "vehicle_model": vehicle_model})
            self.value = normalized
        return self


class BookingSignalCandidate(BaseModel):
    """A booking-scoped fact. Core keys are intentionally typed; custom.* is extensible."""
    category: SignalCategory = Field(description="One of the canonical signal categories.")
    key: str = Field(description=booking_key_schema_description())
    value: Any = Field(description="Value matching the registered booking-key contract.")
    description: str = Field(default="", description="Human-readable evidence; required for custom.* keys.")
    subject: Literal["booking", "booker", "driver", "group"] = Field(description="Booking participant scope for this fact.")
    certainty: Literal["known", "likely", "possible"] = "possible"
    confidence: float = Field(default=0.5, ge=0, le=1)
    source_type: Literal["explicit_user", "implicit_user", "trusted_domain"] = "implicit_user"
    operation: Literal["add", "strengthen", "weaken", "revise", "retract"] = "add"

    def model_post_init(self, __context: Any) -> None:
        self.key = normalize_key(self.key)
        spec = BOOKING_SIGNAL_SPECS.get(self.key)
        if spec is None:
            if not self.key.startswith("custom."):
                raise ValueError("booking signal key must be registered or start with custom.")
            if not self.description.strip():
                raise ValueError("custom booking signal requires a description")
            return
        if self.subject != spec["subject"]:
            raise ValueError(f"{self.key} must use subject={spec['subject']}")
        if spec["value_type"] == "boolean" and not isinstance(self.value, bool):
            raise ValueError(f"{self.key} must be boolean")
        if self.key == "additional_guest_count" and (not isinstance(self.value, int) or isinstance(self.value, bool) or self.value < 0):
            raise ValueError("additional_guest_count must be an integer >= 0")
        if self.key == "additional_guest_context" and not isinstance(self.value, list):
            raise ValueError("additional_guest_context must be a list")
        if spec["value_type"] == "none|low|medium|high" and self.value not in {"none", "low", "medium", "high"}:
            raise ValueError(f"{self.key} must be none, low, medium, or high")


class ProfileSnapshot(BaseModel):
    id: str
    state: Literal["anonymous", "trusted", "merged"]
    version: int = 1
    signals: list[dict[str, Any]] = Field(default_factory=list)
