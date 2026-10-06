from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any, cast

from src.guardrails.models import ProtectedOutput
from src.guardrails.policies import (
    NEVER_PUBLIC_ACTION_DATA_KEYS,
    PUBLIC_TOOL_INPUT_SECRET_KEYS,
    SECRET_VALUE_KEYS,
    canonicalize_sensitive_key,
    is_sensitive_key,
)
from src.guardrails.structure import normalize_text

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE_RE = re.compile(
    r"(?<!\d)(?:(?:\(\s*\+?84\s*\)|\+?84|0)(?:[\s().-]?\d){8,10}|"
    r"\(\s*0\d{2,3}\s*\)(?:[\s.-]?\d){6,8})(?!\d)"
)
_VIETNAM_ID_RE = re.compile(r"(?<!\d)\d{12}(?!\d)")
_STANDALONE_SECRET_RE = re.compile(
    r"(?i)(?<![\w-])(?:"
    r"sk-(?:or-v1-)?[a-z0-9_-]{8,}|"
    r"xox[baprs]-[a-z0-9-]{10,}|"
    r"gh[pousr]_[a-z0-9]{20,}|"
    r"AIza[a-z0-9_-]{20,}|"
    r"eyJ[a-z0-9_-]{8,}\.[a-z0-9_-]{8,}\.[a-z0-9_-]{8,}"
    r")"
)
_CREDENTIAL_ASSIGNMENT_RE = re.compile(
    r"(?i)\b("
    r"(?:openai|openrouter|x)?[_ -]?api[_ -]?key|"
    r"access[_ -]?(?:session[_ -]?)?token|session[_ -]?token|refresh[_ -]?token|"
    r"authorization|client[_ -]?secret|private[_ -]?key|cookie|"
    r"otp(?:[_ -]?code)?|password|secret|token"
    r")\s*[:=]\s*(?:bearer\s+)?([^\s,;]+)"
)
_SYSTEM_PROMPT_LEAK_RE = re.compile(
    r"(?im)(?:"
    r"^-{0,4}\s*(?:system instructions?|developer message|hidden instructions?|active skill guidelines)\s*-{0,4}\s*$|"
    r"<(?:system|developer)(?:\s[^>]*)?>|"
    r"\b(?:system prompt|developer message)\s*[:=]\s*"
    r")"
)
_SAFE_LEAK_FALLBACK = (
    "Tôi không thể hiển thị chỉ dẫn nội bộ hoặc thông tin xác thực. "
    "Tôi có thể hỗ trợ thông tin xe VinFast và đặt lịch lái thử."
)

_PUBLIC_CONTACT_CONTAINER_KEYS = frozenset(
    {"advisor", "salesadvisor", "salesstaff", "showroom", "showrooms"}
)
_PUBLIC_CONTACT_VALUE_KEYS = frozenset({"email", "hotline", "phone"})
_PRIVATE_CONTACT_CONTAINER_KEYS = frozenset(
    {"booker", "customer", "driver", "participant", "person", "profile"}
)


class OutputGuard:
    def __init__(self, *, max_output_chars: int) -> None:
        self.max_output_chars = max_output_chars

    def protect(self, result: Mapping[str, Any]) -> ProtectedOutput:
        secret_values = _collect_secret_values(result)
        public_contacts = _collect_trusted_public_contacts(result.get("action_result"))
        response = self._sanitize_text(
            result.get("response", ""),
            secret_values=secret_values,
            public_contacts=public_contacts,
        )
        action_error = self._sanitize_text(result.get("action_error", ""), secret_values=secret_values)
        action_input = result.get("action_input")
        tool_input = _redact_mapping(
            cast(Mapping[str, Any], action_input) if isinstance(action_input, Mapping) else {},
            blocked_keys=PUBLIC_TOOL_INPUT_SECRET_KEYS,
        )
        action_data = _redact_value(result.get("action_result"), blocked_keys=NEVER_PUBLIC_ACTION_DATA_KEYS)
        return ProtectedOutput(
            response=response,
            # Internal reasoning is never part of the public API contract.
            analysis="",
            tool_input=tool_input,
            action_data=action_data,
            action_error=action_error,
        )

    def _sanitize_text(
        self,
        value: Any,
        *,
        secret_values: set[str],
        public_contacts: set[str] | None = None,
    ) -> str:
        text = normalize_text(value if isinstance(value, str) else str(value or ""))
        if _SYSTEM_PROMPT_LEAK_RE.search(text):
            return _SAFE_LEAK_FALLBACK

        # Only backend tool data under an explicitly public role may exempt a
        # contact from PII redaction. Model text and customer/driver contacts
        # stay private by default.
        placeholders: dict[str, str] = {}
        allowed_contacts = (public_contacts or set()) - secret_values
        for index, contact in enumerate(sorted(allowed_contacts, key=len, reverse=True)):
            normalized_contact = normalize_text(contact)
            if normalized_contact and normalized_contact in text:
                placeholder = f"PUBLICCONTACTPLACEHOLDER{index}"
                text = text.replace(normalized_contact, placeholder)
                placeholders[placeholder] = normalized_contact

        for secret in sorted(secret_values, key=len, reverse=True):
            if len(secret) >= 4:
                text = text.replace(secret, "[redacted]")
        text = _CREDENTIAL_ASSIGNMENT_RE.sub(lambda match: f"{match.group(1)}=[redacted]", text)
        text = _STANDALONE_SECRET_RE.sub("[redacted]", text)
        text = _EMAIL_RE.sub("[email]", text)
        text = _PHONE_RE.sub("[phone]", text)
        text = _VIETNAM_ID_RE.sub("[personal-id]", text)
        for placeholder, contact in placeholders.items():
            text = text.replace(placeholder, contact)
        if len(text) > self.max_output_chars:
            text = text[: self.max_output_chars] + "…[truncated]"
        return text


def _collect_secret_values(value: Any, *, key: str = "") -> set[str]:
    found: set[str] = set()
    if is_sensitive_key(key, SECRET_VALUE_KEYS) and isinstance(value, str) and value:
        found.add(value)
    if isinstance(value, Mapping):
        for nested_key, nested in value.items():
            found.update(_collect_secret_values(nested, key=str(nested_key)))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for nested in value:
            found.update(_collect_secret_values(nested, key=key))
    return found


def _collect_trusted_public_contacts(
    value: Any,
    *,
    path: tuple[str, ...] = (),
) -> set[str]:
    """Read public contacts only from typed backend action-result containers."""
    found: set[str] = set()
    if isinstance(value, Mapping):
        for nested_key, nested in value.items():
            canonical_key = canonicalize_sensitive_key(str(nested_key))
            nested_path = (*path, canonical_key)
            has_public_source = any(key in _PUBLIC_CONTACT_CONTAINER_KEYS for key in path)
            has_private_source = any(key in _PRIVATE_CONTACT_CONTAINER_KEYS for key in path)
            if (
                canonical_key in _PUBLIC_CONTACT_VALUE_KEYS
                and has_public_source
                and not has_private_source
                and isinstance(nested, str)
                and nested
            ):
                found.add(normalize_text(nested))
            found.update(_collect_trusted_public_contacts(nested, path=nested_path))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for nested in value:
            found.update(_collect_trusted_public_contacts(nested, path=path))
    return found


def _redact_mapping(value: Mapping[str, Any], *, blocked_keys: frozenset[str]) -> dict[str, Any]:
    return {
        str(key): _redact_value(nested, key=str(key), blocked_keys=blocked_keys)
        for key, nested in value.items()
    }


def _redact_value(value: Any, *, key: str = "", blocked_keys: frozenset[str]) -> Any:
    if is_sensitive_key(key, blocked_keys):
        return "[redacted]"
    if isinstance(value, Mapping):
        return _redact_mapping(value, blocked_keys=blocked_keys)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_redact_value(item, blocked_keys=blocked_keys) for item in value]
    return value
