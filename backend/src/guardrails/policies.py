"""Central policy constants.

Keeping policy data separate from enforcement code makes reviews and future
changes easier. These expressions intentionally target high-confidence attacks
instead of blocking every occurrence of words such as "prompt" or "system".
"""

from __future__ import annotations

import re
from functools import lru_cache

PROMPT_INJECTION_PATTERNS: tuple[tuple[str, str], ...] = (
    (
        "PROMPT_INJECTION_OVERRIDE",
        r"\b(?:ignore|disregard|forget|override|bypass)\b.{0,80}"
        r"\b(?:previous|prior|system|developer|hidden)\b.{0,50}"
        r"\b(?:instruction|instructions|prompt|message|rules?)\b",
    ),
    (
        "PROMPT_INJECTION_OVERRIDE",
        r"\b(?:bỏ\s+qua|phớt\s+lờ|quên|vượt\s+qua|ghi\s+đè)\b.{0,80}"
        r"\b(?:hướng\s+dẫn|chỉ\s+thị|system\s*prompt|luật|quy\s+tắc)\b.{0,50}"
        r"\b(?:trước|trước\s+đó|hệ\s+thống|ẩn)\b",
    ),
    (
        "PROMPT_INJECTION_OVERRIDE",
        r"\b(?:ignore|disregard|forget|override|bypass)\b.{0,50}"
        r"\b(?:everything|all)\b.{0,30}\b(?:above|before|earlier)\b",
    ),
    (
        "PROMPT_INJECTION_OVERRIDE",
        # A direct compact override at the start of the request (optionally
        # after the observed "show room" filler) is itself imperative enough
        # to block, even when no second command follows it.
        r"^\s*(?:show\s*rooms?\s+)?(?:(?:please|kindly)\s+)?"
        r"(?:ignore|disregard|forget|override|bypass)\s+"
        r"(?:(?:all|any|the|your|these|those)\s+)?"
        r"(?:instructions?|rules?|prompts?|messages?)\b",
    ),
    (
        "PROMPT_INJECTION_OVERRIDE",
        # Compact English override embedded in an otherwise legitimate booking
        # request. Require imperative framing plus a follow-up command so quoted
        # or explanatory uses of "ignore instructions" remain benign.
        r"(?:^|[;:,.!?]\s*|\bshow\s*rooms?\s+|\b(?:and|then|but)\s+)"
        r"(?:(?:please|kindly)\s+|(?:can|could|would)\s+you\s+)?"
        r"(?:ignore|disregard|forget|override|bypass)\s+"
        r"(?:(?:all|any|the|your|these|those)\s+)?"
        r"(?:instructions?|rules?|prompts?|messages?)\b.{0,140}"
        r"\b(?:and|then|now|show|write|answer|respond|return|tell|find|book|call|pick|"
        r"hay|hãy|và|rồi|viết|trả\s+lời|tìm|đặt|gọi|lấy|cho\s+tôi)\b",
    ),
    (
        "PROMPT_INJECTION_OVERRIDE",
        # Folded Vietnamese pattern: it is evaluated against both normalized
        # and accent-folded text by InputGuard.
        r"(?:^|[;:,.!?]\s*|\b(?:va|roi|nhung)\s+)"
        r"(?:(?:hay|lam\s+on|cu)\s+)?"
        r"(?:bo\s+qua|phot\s+lo|quen|ghi\s+de|vuot\s+qua|lam\s+trai)\s+"
        r"(?:(?:moi|cac|toan\s+bo|nhung)\s+)?"
        r"(?:huong\s+dan|chi\s+dan|chi\s+thi|quy\s+tac|luat)\b.{0,140}"
        r"\b(?:va|roi|bay\s+gio|hay|viet|tra\s+loi|tim|dat|goi|lay|chon|cho\s+toi)\b",
    ),
    (
        "PROMPT_INJECTION_OVERRIDE",
        r"\b(?:bo\s+qua|phot\s+lo|quen|vuot\s+qua|ghi\s+de|lam\s+trai)\b.{0,80}"
        r"\b(?:huong\s+dan|chi\s+thi|system\s*prompt|luat|quy\s+tac)\b.{0,50}"
        r"\b(?:truoc|truoc\s+do|he\s+thong|an)\b",
    ),
    (
        "PROMPT_INJECTION_OVERRIDE",
        r"\b(?:khong\s+can|dung|ngung)\s+(?:tuan\s+theo|lam\s+theo)\b.{0,60}"
        r"\b(?:chi\s+thi|huong\s+dan|quy\s+tac|luat)\b.{0,40}"
        r"\b(?:he\s+thong|truoc|cu)\b",
    ),
    (
        "PROMPT_INJECTION_OVERRIDE",
        r"\b(?:xem|coi)\b.{0,50}\b(?:noi\s+dung|chi\s+dan|quy\s+tac)\b.{0,40}"
        r"\b(?:phia\s+tren|truoc\s+do)\b.{0,40}"
        r"\b(?:vo\s+hieu|khong\s+ton\s+tai|het\s+hieu\s+luc)\b",
    ),
    (
        "PROMPT_INJECTION_OVERRIDE",
        r"\b(?:tu\s+gio|ke\s+tu\s+bay\s+gio)\b.{0,60}"
        r"\b(?:chi\s+lam\s+theo|uu\s+tien)\b.{0,40}"
        r"\b(?:lenh|yeu\s+cau|quy\s+tac)\b.{0,30}\b(?:cua\s+toi|sau\s+day|moi)\b",
    ),
    (
        "PROMPT_INJECTION_OVERRIDE",
        # Decoding is benign by itself. Block only when the decoded payload is
        # also requested to be followed or executed.
        r"\b(?:giai\s+ma|decode)\b.{0,100}"
        r"\b(?:lam\s+theo|thuc\s+thi|execute|run)\b.{0,100}"
        r"\b(?:base64|chuoi|payload|noi\s+dung)\b",
    ),
    (
        "SECRET_EXFILTRATION",
        r"\b(?:reveal|show|print|return|dump|expose|leak)\b.{0,80}"
        r"\b(?:system\s+prompt|developer\s+message|hidden\s+instructions?|api[_ -]?keys?|"
        r"access[_ -]?tokens?|environment\s+variables?|secrets?)\b",
    ),
    (
        "SECRET_EXFILTRATION",
        r"\b(?:hiển\s+thị|tiết\s+lộ|in\s+ra|trả\s+về|đọc\s+ra)\b.{0,80}"
        r"\b(?:system\s*prompt|chỉ\s+thị\s+ẩn|khóa\s*api|api\s*key|"
        r"(?:access|auth|bearer|đăng\s+nhập|truy\s+cập|hệ\s+thống)\s*token|"
        r"token\s*(?:đăng\s+nhập|truy\s+cập|xác\s+thực|hệ\s+thống)|"
        r"biến\s+môi\s+trường|bí\s+mật)\b",
    ),
    (
        "SECRET_EXFILTRATION",
        r"\b(?:hien\s+thi|tiet\s+lo|in\s+ra|tra\s+ve|doc\s+ra)\b.{0,80}"
        r"\b(?:system\s*prompt|chi\s+thi\s+an|khoa\s*api|api\s*key|"
        r"(?:access|auth|bearer|dang\s+nhap|truy\s+cap|he\s+thong)\s*token|"
        r"token\s*(?:dang\s+nhap|truy\s+cap|xac\s+thuc|he\s+thong)|"
        r"bien\s+moi\s+truong|bi\s+mat)\b",
    ),
    (
        "SECRET_EXFILTRATION",
        r"\b(?:cho|gui|dua|lay)\s+(?:giup\s+)?toi\b.{0,80}"
        r"\b(?:(?:access|auth|bearer|dang\s+nhap|truy\s+cap|he\s+thong)\s*token|"
        r"token\s*(?:dang\s+nhap|truy\s+cap|xac\s+thuc|he\s+thong)|"
        r"khoa\s*api|api\s*key|bi\s+mat|chi\s+thi\s+an|system\s*prompt)\b",
    ),
    (
        "PRIVACY_EXFILTRATION",
        r"\b(?:cho|dua|hien\s+thi|tiet\s+lo|tra\s+ve|lay)\b.{0,80}"
        r"\b(?:so\s+dien\s+thoai|email|thong\s+tin\s+lien\s+he)\b.{0,80}"
        r"\b(?:khach|nguoi)\s+khac\b",
    ),
    (
        "PRIVACY_EXFILTRATION",
        # Unverified authority does not grant access to a customer's contact
        # details. Requiring both contact fields and a customer reference keeps
        # ordinary showroom-contact and self-profile requests allowed.
        r"\b(?:gui|cho|dua|lay|hien\s+thi|tiet\s+lo)\b.{0,100}"
        r"\b(?:email|so\s+dien\s+thoai|thong\s+tin\s+lien\s+he)\b.{0,100}"
        r"\b(?:cua\s+)?khach\b.{0,50}\b(?:dang\s+dat|da\s+dat|dat\s+(?:lich|vf)|booking)\b",
    ),
    (
        "PRIVACY_EXFILTRATION",
        r"\b(?:show|give|reveal|return|list)\b.{0,80}"
        r"\b(?:phone\s+numbers?|emails?|contact\s+(?:details|information))\b.{0,80}"
        r"\b(?:another|other)\s+(?:customer|user|person|people)s?\b",
    ),
    (
        "ROLE_INJECTION",
        r"<\s*/?\s*(?:tool_call|function_call|system|developer)\b|"
        r"(?:^|\n)\s*(?:system|developer)\s*:\s*",
    ),
    (
        "ROLE_INJECTION",
        r"\b(?:you\s+are\s+now|act\s+as)\b.{0,50}"
        r"\b(?:linux\s+terminal|shell|developer\s+mode|system\s+administrator)\b",
    ),
)

# High-confidence direct profanity/abuse only. Avoid broad words such as
# "chó" or folded one-syllable forms such as "du" because they create common
# Vietnamese false positives (for example "đủ").
ABUSIVE_LANGUAGE_PATTERNS: tuple[str, ...] = (
    r"\b(?:địt|đụ|đéo|cặc|lồn|buồi)\b",
    r"\b(?:dit\s+(?:me|ma)|du\s+ma|deo\s+(?:me|can|hieu)|vai\s+lon|cai\s+lon|"
    r"con\s+đĩ|suc\s+vat|(?:do|thang|con|may)\s+ngu|oc\s+cho|"
    r"cut\s+(?:di|me)|me\s+may)\b",
    r"\b(?:fuck(?:\s+you)?|motherfucker|asshole|bitch|piece\s+of\s+shit)\b",
)

ABUSE_VIOLATION_CODES = frozenset(
    {
        "ABUSIVE_LANGUAGE",
        "PROMPT_INJECTION_OVERRIDE",
        "ROLE_INJECTION",
        "SECRET_EXFILTRATION",
    }
)

ACTION_ALLOWED_FIELDS: dict[str, frozenset[str]] = {
    "search_options": frozenset(
        {
            "vehicle_model",
            "vehicle_variant",
            "showroom_id",
            "showroom_query",
            "address",
            "preferred_date",
            "preferred_dates",
            "preferred_date_from",
            "preferred_date_to",
            "preferred_time",
            "latitude",
            "longitude",
            "showroom_limit",
            "slot_limit",
        }
    ),
    "hold_slot": frozenset({"slot_id", "ui_action_id"}),
    "update_draft": frozenset(
        {
            "booking_id",
            "booker_patch",
            "driver_patch",
            "driver_same_as_booker",
            "has_valid_license_commitment",
            "notification_plan_patch",
            "expected_version",
        }
    ),
    "confirm_booking": frozenset({"booking_id", "expected_version", "ui_action_id"}),
    "request_access": frozenset({"booking_code", "contact_value", "purpose", "preferred_channel"}),
    "verify_access": frozenset({"challenge_id", "otp_code"}),
    "cancel_booking": frozenset({"booking_id", "access_session_token", "ui_action_id", "reason"}),
    "reschedule_booking": frozenset(
        {"current_booking_id", "new_slot_id", "access_session_token", "ui_action_id"}
    ),
}

PERSON_PATCH_FIELDS = frozenset({"full_name", "phone", "email", "preferred_channel"})
NOTIFICATION_PATCH_FIELDS = frozenset(
    {
        "copy_booker",
        "zalo_enabled",
        "sms_enabled",
        "email_enabled",
        "reminder_24h_enabled",
        "reminder_2h_enabled",
    }
)
LICENSE_PATCH_FIELDS = frozenset(
    {
        "has_driving_license",
        "has_valid_license_commitment",
        "declared_license_class",
        "validity_acknowledged",
    }
)

# Nested object contracts close the gap left by top-level allowlists. Domain
# services still own type/required/business validation; this policy only blocks
# fields that can never be accepted at the public action boundary.
ACTION_NESTED_ALLOWED_FIELDS: dict[str, dict[str, frozenset[str]]] = {
    "update_draft": {
        "booker_patch": PERSON_PATCH_FIELDS,
        "driver_patch": PERSON_PATCH_FIELDS,
        "notification_plan_patch": NOTIFICATION_PATCH_FIELDS,
    }
}

# UI context is untrusted reference data, not an instruction channel. Keep this
# contract synchronized with frontend/src/api/booking.js.
CONTEXT_ALLOWED_FIELDS = frozenset(
    {
        "channel",
        "stage",
        "recipient",
        "selectedVehicle",
        "selectedShowroom",
        "selectedSlot",
        "nearbyShowrooms",
        "userLocation",
        "bookingId",
        "pendingReschedule",
    }
)
CONTEXT_NESTED_ALLOWED_FIELDS: dict[str, frozenset[str]] = {
    "selectedVehicle": frozenset({"id", "name"}),
    "selectedShowroom": frozenset({"id", "name"}),
    "selectedSlot": frozenset({"slotId", "time", "dateLabel", "isAvailable", "unavailableLabel"}),
    "userLocation": frozenset({"latitude", "longitude"}),
    "nearbyShowrooms": frozenset({"id", "name", "address", "distance"}),
    "pendingReschedule": frozenset(
        {"reschedule_date_type", "reschedule_target_date", "reschedule_day_offset", "reschedule_target_time"}
    ),
}

# `/demo/action` is also a public tool boundary, even though it bypasses the
# LLM. Keep a separate contract because it exposes additional authenticated
# booking-management commands.
DEMO_ACTION_ALLOWED_FIELDS: dict[str, frozenset[str]] = {
    "search_options": ACTION_ALLOWED_FIELDS["search_options"],
    "hold_slot": ACTION_ALLOWED_FIELDS["hold_slot"],
    "get_draft": frozenset({"booking_id"}),
    "list_bookings": frozenset({"access_session_token"}),
    "update_draft": frozenset(
        {
            "booking_id",
            "booker_patch",
            "driver_patch",
            "driver_same_as_booker",
            "license_patch",
            "notification_plan_patch",
            "expected_version",
        }
    ),
    "confirm_booking": ACTION_ALLOWED_FIELDS["confirm_booking"],
    "request_access": ACTION_ALLOWED_FIELDS["request_access"],
    "verify_access": ACTION_ALLOWED_FIELDS["verify_access"],
    "get_details": frozenset({"access_session_token", "booking_id", "booking_code"}),
    "update_details": frozenset(
        {"booking_id", "access_session_token", "booker_patch", "driver_patch", "driver_same_as_booker"}
    ),
    "search_reschedule": frozenset(
        {
            "current_booking_id",
            "access_session_token",
            "date_type",
            "target_date",
            "day_offset",
            "target_time",
        }
    ),
    "hold_reschedule": frozenset(
        {"current_booking_id", "new_slot_id", "access_session_token", "ui_action_id"}
    ),
    "confirm_reschedule": frozenset(
        {"current_booking_id", "new_booking_id", "access_session_token", "ui_action_id"}
    ),
    "cancel_booking": frozenset({"booking_id", "access_session_token", "ui_action_id", "reason"}),
    "release_hold": frozenset({"booking_id"}),
}

DEMO_ACTION_NESTED_ALLOWED_FIELDS: dict[str, dict[str, frozenset[str]]] = {
    "update_draft": {
        "booker_patch": PERSON_PATCH_FIELDS,
        "driver_patch": PERSON_PATCH_FIELDS,
        "license_patch": LICENSE_PATCH_FIELDS,
        "notification_plan_patch": NOTIFICATION_PATCH_FIELDS,
    },
    "update_details": {
        "booker_patch": PERSON_PATCH_FIELDS,
        "driver_patch": PERSON_PATCH_FIELDS,
    },
}

MUTATING_TOOL_NAMES = frozenset(
    {
        "hold_test_drive_slot",
        "update_booking_draft",
        "confirm_test_drive_booking",
        "request_booking_access",
        "verify_booking_access",
        "cancel_booking",
        "reschedule_booking",
    }
)

CONFIRMATION_TOOL_NAMES = frozenset(
    {"confirm_test_drive_booking", "cancel_booking", "reschedule_booking"}
)
CONFIRMATION_ACTION_BY_TOOL = {
    "confirm_test_drive_booking": "confirm_booking",
    "cancel_booking": "cancel_booking",
    "reschedule_booking": "reschedule_booking",
}
CONFIRMATION_BOUND_FIELDS_BY_TOOL = {
    "confirm_test_drive_booking": frozenset({"booking_id", "expected_version", "ui_action_id"}),
    "cancel_booking": frozenset({"booking_id", "access_session_token", "ui_action_id"}),
    "reschedule_booking": frozenset(
        {"current_booking_id", "new_slot_id", "access_session_token", "ui_action_id"}
    ),
}

# Values under these keys are never safe in natural-language output or public
# diagnostic fields. Some keys are still intentionally present in action_data so
# the authenticated frontend can continue an OTP workflow.
SECRET_VALUE_KEYS = frozenset(
    {
        "access_session_token",
        "access_token",
        "api_key",
        "authorization",
        "challenge_id",
        "client_secret",
        "code_hash",
        "contact_value",
        "conversation_id",
        "conversation_token",
        "cookie",
        "destination_hash",
        "license_number",
        "openai_api_key",
        "openrouter_api_key",
        "otp",
        "otp_code",
        "password",
        "private_key",
        "refresh_token",
        "secret",
        "session_token",
        "token",
        "token_hash",
        "x_api_key",
        "zalo_bot_token",
    }
)

PUBLIC_TOOL_INPUT_SECRET_KEYS = SECRET_VALUE_KEYS | frozenset(
    {"email", "normalized_email", "normalized_phone", "phone"}
)

# action_data is a machine-readable workflow channel. The browser needs
# challenge_id/access_session_token, but raw OTPs and backend credentials must
# never cross this boundary.
NEVER_PUBLIC_ACTION_DATA_KEYS = frozenset(
    {
        "access_token",
        "api_key",
        "authorization",
        "client_secret",
        "code_hash",
        "cookie",
        "destination_hash",
        "openai_api_key",
        "openrouter_api_key",
        "otp",
        "otp_code",
        "password",
        "private_key",
        "refresh_token",
        "secret",
        "session_token",
        "token",
        "token_hash",
        "x_api_key",
        "zalo_bot_token",
    }
)


def canonicalize_sensitive_key(key: str) -> str:
    """Make snake-, kebab-, space- and camel-style keys comparable."""
    return re.sub(r"[^a-z0-9]", "", key.casefold())


@lru_cache(maxsize=16)
def _canonical_sensitive_keys(sensitive_keys: frozenset[str]) -> frozenset[str]:
    return frozenset(canonicalize_sensitive_key(item) for item in sensitive_keys)


def is_sensitive_key(key: str, sensitive_keys: frozenset[str]) -> bool:
    candidate = canonicalize_sensitive_key(key)
    return candidate in _canonical_sensitive_keys(sensitive_keys)
