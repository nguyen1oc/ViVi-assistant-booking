import re
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

NAME_MAX_LENGTH = 30
PHONE_LENGTH = 10
EMAIL_LOCAL_MAX_LENGTH = 30
EMAIL_DOMAIN_MAX_LENGTH = 20


def utcnow() -> datetime:
    return datetime.now(UTC)


def iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def parse_utc(value: str | datetime) -> datetime:
    """Parse a persisted timestamp into one UTC-aware datetime.

    Legacy CSV rows without an offset are interpreted as UTC. New imports are
    normalized back to an explicit ``+00:00`` representation before storage.
    """
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def normalize_timestamp(value: str | datetime) -> str:
    """Return the canonical persisted representation for an instant in time."""
    return iso(parse_utc(value))


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def normalize_phone(value: str | None) -> str | None:
    if not value:
        return None
    digits = re.sub(r"\D", "", value)
    return f"0{digits[2:]}" if digits.startswith("84") else digits


def is_valid_customer_email(value: str | None) -> bool:
    text = (value or "").strip()
    if text.count("@") != 1:
        return False
    local, domain = text.split("@")
    return (
        bool(local and domain)
        and len(local) <= EMAIL_LOCAL_MAX_LENGTH
        and len(domain) <= EMAIL_DOMAIN_MAX_LENGTH
        and re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", text) is not None
    )


def is_valid_customer_phone(value: str | None) -> bool:
    normalized = normalize_phone(value)
    return bool(normalized and len(normalized) == PHONE_LENGTH and normalized.startswith("0") and normalized.isdigit())


def person_patch_validation_error(patch: dict | None) -> str | None:
    if not patch:
        return None
    if "full_name" in patch and len(str(patch.get("full_name") or "").strip()) > NAME_MAX_LENGTH:
        return f"Họ tên tối đa {NAME_MAX_LENGTH} ký tự."
    if "email" in patch and not is_valid_customer_email(str(patch.get("email") or "")):
        return "Email phải đúng định dạng, tối đa 30 ký tự trước @ và 20 ký tự sau @."
    if "phone" in patch and patch.get("phone") and not is_valid_customer_phone(str(patch["phone"])):
        return "Số điện thoại phải gồm đúng 10 chữ số và bắt đầu bằng 0."
    return None


def row_to_dict(row) -> dict[str, Any] | None:
    return dict(row) if row else None
