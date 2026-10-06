"""Canonical signal contracts shared by tool schemas and persistence validation."""

from __future__ import annotations

from typing import Any, Literal, get_args

SignalCategory = Literal[
    "fact", "usage", "experience", "interest", "concern", "test_drive_goal",
    "conversation_preference", "custom_intent",
]
ALLOWED_CATEGORIES = frozenset(get_args(SignalCategory))

# ``value_type`` is intentionally human-readable: it is used in the tool
# description as well as validated by the Pydantic candidates below.
PROFILE_SIGNAL_SPECS: dict[str, dict[str, Any]] = {
    "household_size": {"category": "fact", "value_type": "integer >= 1"},
    "primary_use": {
        "category": "usage",
        "value_type": "list of usage labels",
        "recommended_values": ["urban_commute", "highway_commute", "long_trip", "family_use"],
    },
    "commute_distance_km": {"category": "usage", "value_type": "number >= 0"},
    "ev_experience": {
        "category": "experience",
        "value_type": "experience label",
        "recommended_values": ["first_ev", "ev_owner", "ev_experienced"],
    },
    "home_charging_access": {
        "category": "fact",
        "value_type": "boolean or charging-access label",
        "recommended_values": [
            "home_charging_available", "apartment_no_home_charging",
            "workplace_charging", "no_regular_charging",
        ],
    },
    "vehicle_interest": {"category": "interest", "value_type": "model or model list"},
    "feature_interest": {
        "category": "interest",
        "value_type": "list of feature/topic labels",
        "recommended_values": [
            "charging", "adas", "parking_cameras_and_sensors", "phone_connectivity",
            "comfort", "noise_insulation", "cargo_space",
        ],
    },
    "policy_interest": {
        "category": "interest",
        "value_type": "list of {topic, vehicle_model} objects",
        "recommended_values": ["maintenance", "warranty", "after_sales_policy", "insurance"],
    },
    "test_drive_priority": {
        "category": "test_drive_goal",
        "value_type": "list of things to evaluate",
        "recommended_values": [
            "parking_and_vehicle_size", "family_space_and_comfort",
            "child_seat_fit_and_access", "elderly_entry_exit_comfort", "cargo_fit",
            "noise_insulation", "ride_comfort", "urban_maneuvering", "highway_stability",
        ],
    },
    "current_vehicle_pain_points": {
        "category": "concern",
        "value_type": "list of current-vehicle pain-point labels",
        "recommended_values": [
            "parking", "rear_space", "ride_comfort", "noise", "cargo_space", "tech", "charging",
        ],
    },
    "response_style": {"category": "conversation_preference", "value_type": "style preference"},
}
PROFILE_SIGNAL_KEY_ALIASES = {
    "urban_commute": "primary_use",
    "city_commute": "primary_use",
    "first_ev": "ev_experience",
    "first_time_ev": "ev_experience",
}
BOOKING_SIGNAL_SPECS: dict[str, dict[str, Any]] = {
    "booker_attending": {"subject": "booker", "value_type": "boolean"},
    "driver_attending": {"subject": "driver", "value_type": "boolean"},
    "booker_will_drive": {"subject": "booker", "value_type": "boolean"},
    "driver_will_drive": {"subject": "driver", "value_type": "boolean"},
    "booker_evaluation_involvement": {"subject": "booker", "value_type": "none|low|medium|high"},
    "driver_evaluation_involvement": {"subject": "driver", "value_type": "none|low|medium|high"},
    "booker_purchase_involvement": {"subject": "booker", "value_type": "none|low|medium|high"},
    "driver_purchase_involvement": {"subject": "driver", "value_type": "none|low|medium|high"},
    "additional_guest_count": {"subject": "group", "value_type": "integer >= 0"},
    "additional_guest_context": {"subject": "group", "value_type": "array"},
}


def normalize_key(value: str) -> str:
    normalized = "_".join(value.casefold().strip().replace("-", " ").split())
    return "".join(char for char in normalized if char.isalnum() or char in {"_", "."})[:100]


def canonical_profile_key(value: str) -> str:
    normalized = normalize_key(value)
    return PROFILE_SIGNAL_KEY_ALIASES.get(normalized, normalized)


def profile_key_schema_description() -> str:
    contracts = "; ".join(
        f"{key} ({spec['category']}; {spec['value_type']}"
        f"; recommended: {', '.join(spec['recommended_values'])})"
        if spec.get("recommended_values")
        else f"{key} ({spec['category']}; {spec['value_type']})"
        for key, spec in PROFILE_SIGNAL_SPECS.items()
    )
    return f"Registered keys: {contracts}. Otherwise use custom.<name> with description."


def booking_key_schema_description() -> str:
    contracts = "; ".join(
        f"{key} (subject={spec['subject']}; {spec['value_type']})"
        for key, spec in BOOKING_SIGNAL_SPECS.items()
    )
    return f"Registered keys: {contracts}. Otherwise use custom.<name> with description."
