from __future__ import annotations

import math
import re
from collections.abc import Mapping
from typing import Any

from src.guardrails.models import GuardrailDecision
from src.guardrails.policies import (
    ABUSIVE_LANGUAGE_PATTERNS,
    ACTION_ALLOWED_FIELDS,
    ACTION_NESTED_ALLOWED_FIELDS,
    CONTEXT_ALLOWED_FIELDS,
    CONTEXT_NESTED_ALLOWED_FIELDS,
    PROMPT_INJECTION_PATTERNS,
)
from src.guardrails.structure import (
    PayloadLimits,
    fold_text_for_policy,
    iter_strings,
    normalize_text,
    validate_payload,
)

_SAFE_CONVERSATION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,99}$")

_BLOCKED_MESSAGE = (
    "Yêu cầu này có dấu hiệu cố gắng thay đổi chỉ dẫn hoặc truy cập thông tin nội bộ, "
    "nên ViVi không thể xử lý. ViVi vẫn có thể hỗ trợ thông tin xe VinFast và đặt lịch lái thử."
)
_ABUSIVE_BLOCKED_MESSAGE = (
    "Tin nhắn có ngôn ngữ tục hoặc xúc phạm nên đã bị chặn. "
    "Vui lòng trao đổi lịch sự để tiếp tục sử dụng trợ lý."
)
_INVALID_PAYLOAD_MESSAGE = "Dữ liệu gửi lên không hợp lệ hoặc quá phức tạp. Vui lòng tải lại trang và thử lại."
_CONTEXT_STRING_MAX_CHARS = 500
_CONTEXT_LIST_MAX_ITEMS = 30
_LEGACY_CONTEXT_FIELDS = frozenset(
    {
        "mode",
        "phase",
        "allowed_actions",
        "selected_vehicle_id",
        "selected_vehicle_name",
        "selected_showroom_id",
        "selected_showroom_name",
        "selected_slot_id",
        "selected_slot_time",
        "selected_slot_date",
        "booking_id",
        "nearby_showrooms",
    }
)
_LEGACY_PHASE_TO_STAGE = {
    "idle": "idle",
    "choose_vehicle": "need_car",
    "choose_location": "need_address",
    "choose_showroom": "choose_showroom",
    "choose_slot": "choose_slot",
    "collect_info": "collect_info",
    "review": "review",
    "success": "success",
    "access_request": "lookup",
    "access_verify": "lookup",
    "booking_list": "lookup",
    "booking_edit": "lookup",
    "booking_cancel_confirm": "lookup",
    "reschedule_showroom": "lookup",
    "reschedule_slot": "lookup",
    "reschedule_confirm": "lookup",
}
_CONTEXT_STAGES = frozenset(
    {
        "idle",
        "lookup",
        "need_car",
        "need_address",
        "choose_showroom",
        "choose_slot",
        "collect_info",
        "review",
        "success",
    }
)
_SHOWROOM_CONTEXT_STAGES = frozenset({"choose_slot", "collect_info", "review", "success"})
_SLOT_CONTEXT_STAGES = frozenset({"collect_info", "review", "success"})
_NEARBY_SHOWROOM_CONTEXT_STAGES = frozenset({"choose_showroom", "choose_slot"})

_QUOTED_SPAN_RE = re.compile(
    r'"[^"\n]*"|\'[^\'\n]*\'|`[^`\n]*`|“[^”\n]*”',
    re.IGNORECASE,
)
_SECURITY_VOCABULARY_RE = re.compile(
    r"\b(?:ignore|disregard|override|bypass|prompt\s+injection|system\s+prompt|"
    r"bo\s+qua|phot\s+lo|ghi\s+de|vuot\s+qua|chi\s+thi\s+an)\b",
    re.IGNORECASE,
)
_EXPLANATORY_SECURITY_RE = re.compile(
    r"\b(?:explain|meaning|what\s+does|why\s+is|example\s+of|quoted|quote|"
    r"giai\s+thich|nghia\s+la\s+gi|tai\s+sao|vi\s+sao|phan\s+tich|"
    r"vi\s+du|trich\s+dan|cau|cum\s+tu)\b",
    re.IGNORECASE,
)
_EXPLICIT_EXECUTION_RE = re.compile(
    r"\b(?:please|kindly|hay|vui\s+long)\s+(?:execute|run|follow|obey|"
    r"ignore|disregard|override|bypass|bo\s+qua|ghi\s+de|"
    r"lam\s+theo|thuc\s+thi|thuc\s+hien|ap\s+dung)\b|"
    r"\b(?:and\s+then|then|roi|sau\s+do)\b.{0,80}"
    r"\b(?:reveal|show|dump|execute|run|ignore|disregard|override|bypass|"
    r"bo\s+qua|ghi\s+de|tiet\s+lo|hien\s+thi|in\s+ra)\b",
    re.IGNORECASE | re.DOTALL,
)
_QUOTED_IMPERATIVE_RE = re.compile(
    r"^\s*(?:please|kindly|hay|vui\s+long)\b(?!\s*(?:explain|analyze|"
    r"giai\s+thich|phan\s+tich))",
    re.IGNORECASE,
)


def _is_benign_security_discussion(value: str) -> bool:
    """Allow quoted or explanatory security vocabulary, never an execution request."""
    folded = fold_text_for_policy(value)
    quoted_spans = _QUOTED_SPAN_RE.findall(folded)
    without_quotes = _QUOTED_SPAN_RE.sub(" ", folded)
    quoted_example = any(_SECURITY_VOCABULARY_RE.search(span) for span in quoted_spans)
    explanatory = bool(_EXPLANATORY_SECURITY_RE.search(folded))
    if not quoted_example and not explanatory:
        return False
    execution_text = without_quotes if quoted_example else folded
    return not (
        _EXPLICIT_EXECUTION_RE.search(execution_text)
        or (quoted_example and _QUOTED_IMPERATIVE_RE.search(execution_text))
    )


class InputGuard:
    def __init__(self, payload_limits: PayloadLimits) -> None:
        self.payload_limits = payload_limits
        self._injection_patterns = tuple(
            (code, re.compile(expression, re.IGNORECASE | re.DOTALL))
            for code, expression in PROMPT_INJECTION_PATTERNS
        )
        self._abusive_patterns = tuple(
            re.compile(expression, re.IGNORECASE | re.DOTALL)
            for expression in ABUSIVE_LANGUAGE_PATTERNS
        )

    def inspect(
        self,
        *,
        message: str,
        conversation_id: str,
        context: dict[str, Any],
        action: str | None,
        action_payload: dict[str, Any],
    ) -> GuardrailDecision:
        normalized_message = normalize_text(message)
        if not normalized_message:
            return GuardrailDecision.block(
                "EMPTY_MESSAGE",
                "message is empty after normalization",
                "Tin nhắn không được để trống.",
            )

        if conversation_id and not _SAFE_CONVERSATION_ID.fullmatch(conversation_id):
            return GuardrailDecision.block(
                "INVALID_CONVERSATION_ID",
                "conversation_id contains unsupported characters",
                _INVALID_PAYLOAD_MESSAGE,
            )

        for label, payload in (("context", context), ("action_payload", action_payload)):
            payload_decision = self.inspect_payload(payload, label=label)
            if not payload_decision.allowed:
                return payload_decision

        # Scan before enforcing the context contract so a known injection keeps
        # its specific operational code instead of being reported only as an
        # unknown UI field.
        candidates = [normalized_message, *iter_strings(context)]
        for candidate in candidates:
            normalized_candidate = normalize_text(candidate)
            folded_candidate = fold_text_for_policy(normalized_candidate)
            benign_security_discussion = _is_benign_security_discussion(normalized_candidate)
            for code, pattern in self._injection_patterns:
                if benign_security_discussion and code in {
                    "PROMPT_INJECTION_OVERRIDE",
                    "ROLE_INJECTION",
                }:
                    continue
                if pattern.search(normalized_candidate) or pattern.search(folded_candidate):
                    return GuardrailDecision.block(
                        code,
                        "high-confidence prompt/role injection pattern matched",
                        _BLOCKED_MESSAGE,
                    )
            if any(
                pattern.search(normalized_candidate) or pattern.search(folded_candidate)
                for pattern in self._abusive_patterns
            ):
                return GuardrailDecision.block(
                    "ABUSIVE_LANGUAGE",
                    "high-confidence abusive language pattern matched",
                    _ABUSIVE_BLOCKED_MESSAGE,
                )

        context_decision = self.inspect_context(context)
        if not context_decision.allowed:
            return context_decision
        sanitized_context = context_decision.sanitized_context or {}

        if action:
            action_decision = self.inspect_structured_payload(
                action=action,
                payload=action_payload,
                contracts=ACTION_ALLOWED_FIELDS,
                nested_contracts=ACTION_NESTED_ALLOWED_FIELDS,
            )
            if not action_decision.allowed:
                return action_decision

        return GuardrailDecision.allow(
            sanitized_text=normalized_message,
            sanitized_context=sanitized_context,
        )

    def inspect_context(self, context: Mapping[str, Any]) -> GuardrailDecision:
        payload_decision = self.inspect_payload(context, label="context")
        if not payload_decision.allowed:
            return payload_decision
        unexpected = sorted(set(map(str, context)) - CONTEXT_ALLOWED_FIELDS - _LEGACY_CONTEXT_FIELDS)
        if unexpected:
            return GuardrailDecision.block(
                "CONTEXT_FIELDS_NOT_ALLOWED",
                "UI context contains fields outside its public contract",
                _INVALID_PAYLOAD_MESSAGE,
                details={"fields": unexpected},
            )

        context = self._canonicalize_context(context)

        sanitized: dict[str, Any] = {}
        for key, value in context.items():
            if value is None:
                sanitized[key] = None
                continue
            if key == "nearbyShowrooms":
                if not isinstance(value, list) or len(value) > _CONTEXT_LIST_MAX_ITEMS:
                    return self._invalid_context_type(key)
                items: list[dict[str, Any]] = []
                for item in value:
                    decision, cleaned = self._inspect_context_object(key, item)
                    if decision is not None:
                        return decision
                    items.append(cleaned)
                sanitized[key] = items
                continue
            if key in CONTEXT_NESTED_ALLOWED_FIELDS:
                decision, cleaned = self._inspect_context_object(key, value)
                if decision is not None:
                    return decision
                sanitized[key] = cleaned
                continue
            if not isinstance(value, str) or len(value) > _CONTEXT_STRING_MAX_CHARS:
                return self._invalid_context_type(key)
            cleaned_value = normalize_text(value)
            if key == "channel" and cleaned_value not in {"booking", "driver_invitation"}:
                return self._invalid_context_value(key)
            if key == "stage" and cleaned_value not in _CONTEXT_STAGES:
                return self._invalid_context_value(key)
            if key == "recipient" and cleaned_value not in {"", "self", "other"}:
                return self._invalid_context_value(key)
            sanitized[key] = cleaned_value

        # UI state is advisory and may be restored from an older browser session.
        # Keep only fields that are coherent with the current workflow stage so a
        # stale confirmed booking cannot silently anchor a brand-new availability search.
        stage = str(sanitized.get("stage") or "")
        if stage not in _SHOWROOM_CONTEXT_STAGES:
            sanitized.pop("selectedShowroom", None)
        if stage not in _SLOT_CONTEXT_STAGES:
            sanitized.pop("selectedSlot", None)
            sanitized.pop("bookingId", None)
        if stage not in _NEARBY_SHOWROOM_CONTEXT_STAGES:
            sanitized.pop("nearbyShowrooms", None)
            sanitized.pop("userLocation", None)
        return GuardrailDecision.allow(sanitized_context=sanitized)

    @staticmethod
    def _canonicalize_context(context: Mapping[str, Any]) -> dict[str, Any]:
        """Normalize the temporary legacy UI contract into the canonical one.

        Legacy fields are accepted only during the frontend/backend rollout and
        are never forwarded to the agent. Canonical nested objects always win
        when a mixed payload contains both representations.
        """
        canonical = {key: value for key, value in context.items() if key in CONTEXT_ALLOWED_FIELDS}

        if not str(canonical.get("stage") or "").strip():
            phase = str(context.get("phase") or "").strip()
            stage = _LEGACY_PHASE_TO_STAGE.get(phase)
            if stage:
                canonical["stage"] = stage
            else:
                canonical.pop("stage", None)

        def legacy_object(target: str, fields: Mapping[str, str]) -> None:
            if target in canonical:
                return
            value = {
                nested: context.get(source)
                for nested, source in fields.items()
                if context.get(source) not in (None, "")
            }
            if value:
                canonical[target] = value

        legacy_object(
            "selectedVehicle",
            {"id": "selected_vehicle_id", "name": "selected_vehicle_name"},
        )
        legacy_object(
            "selectedShowroom",
            {"id": "selected_showroom_id", "name": "selected_showroom_name"},
        )
        legacy_object(
            "selectedSlot",
            {
                "slotId": "selected_slot_id",
                "time": "selected_slot_time",
                "dateLabel": "selected_slot_date",
            },
        )

        if "bookingId" not in canonical and context.get("booking_id") not in (None, ""):
            canonical["bookingId"] = context["booking_id"]
        if "nearbyShowrooms" not in canonical and isinstance(context.get("nearby_showrooms"), list):
            canonical["nearbyShowrooms"] = context["nearby_showrooms"]

        # These legacy fields represented client-owned workflow decisions and
        # are intentionally ignored: mode, allowed_actions and raw phase.
        return canonical

    def _inspect_context_object(
        self,
        field: str,
        value: Any,
    ) -> tuple[GuardrailDecision | None, dict[str, Any]]:
        if not isinstance(value, Mapping):
            return self._invalid_context_type(field), {}
        allowed_fields = CONTEXT_NESTED_ALLOWED_FIELDS[field]
        unexpected = sorted(set(map(str, value)) - allowed_fields)
        if unexpected:
            return (
                GuardrailDecision.block(
                    "CONTEXT_FIELDS_NOT_ALLOWED",
                    "UI context contains nested fields outside its public contract",
                    _INVALID_PAYLOAD_MESSAGE,
                    details={"field": field, "fields": unexpected},
                ),
                {},
            )
        cleaned: dict[str, Any] = {}
        for key, nested in value.items():
            if nested is None or isinstance(nested, bool):
                cleaned[str(key)] = nested
            elif isinstance(nested, str) and len(nested) <= _CONTEXT_STRING_MAX_CHARS:
                cleaned[str(key)] = normalize_text(nested)
            elif isinstance(nested, (int, float)) and not isinstance(nested, bool) and math.isfinite(nested):
                if key == "latitude" and not -90 <= nested <= 90:
                    return self._invalid_context_value(f"{field}.{key}"), {}
                if key == "longitude" and not -180 <= nested <= 180:
                    return self._invalid_context_value(f"{field}.{key}"), {}
                if key == "distance" and nested < 0:
                    return self._invalid_context_value(f"{field}.{key}"), {}
                cleaned[str(key)] = nested
            else:
                return self._invalid_context_type(f"{field}.{key}"), {}
        return None, cleaned

    @staticmethod
    def _invalid_context_type(field: str) -> GuardrailDecision:
        return GuardrailDecision.block(
            "CONTEXT_FIELD_TYPE_INVALID",
            f"UI context field has an invalid type: {field}",
            _INVALID_PAYLOAD_MESSAGE,
            details={"field": field},
        )

    @staticmethod
    def _invalid_context_value(field: str) -> GuardrailDecision:
        return GuardrailDecision.block(
            "CONTEXT_FIELD_VALUE_INVALID",
            f"UI context field has an invalid value: {field}",
            _INVALID_PAYLOAD_MESSAGE,
            details={"field": field},
        )

    def inspect_payload(self, payload: Any, *, label: str) -> GuardrailDecision:
        violation = validate_payload(payload, self.payload_limits)
        if violation:
            return GuardrailDecision.block(
                "PAYLOAD_LIMIT_EXCEEDED",
                f"{label}: {violation}",
                _INVALID_PAYLOAD_MESSAGE,
                details={"field": label},
            )
        return GuardrailDecision.allow()

    def inspect_structured_payload(
        self,
        *,
        action: str,
        payload: dict[str, Any],
        contracts: dict[str, frozenset[str]],
        nested_contracts: dict[str, dict[str, frozenset[str]]] | None = None,
    ) -> GuardrailDecision:
        payload_decision = self.inspect_payload(payload, label="action_payload")
        if not payload_decision.allowed:
            return payload_decision
        allowed_fields = contracts.get(action)
        if allowed_fields is None:
            return GuardrailDecision.block(
                "ACTION_NOT_ALLOWED",
                f"structured action is not allowlisted: {action}",
                "Thao tác này không được hỗ trợ.",
            )
        unexpected = sorted(set(payload) - allowed_fields)
        if unexpected:
            return GuardrailDecision.block(
                "ACTION_FIELDS_NOT_ALLOWED",
                "structured action contains fields outside its contract",
                _INVALID_PAYLOAD_MESSAGE,
                details={"action": action, "fields": unexpected},
            )
        for field, nested_allowed_fields in (nested_contracts or {}).get(action, {}).items():
            nested_value = payload.get(field)
            if nested_value is None:
                continue
            if not isinstance(nested_value, Mapping):
                return GuardrailDecision.block(
                    "ACTION_FIELD_TYPE_INVALID",
                    f"structured action field must be an object: {action}.{field}",
                    _INVALID_PAYLOAD_MESSAGE,
                    details={"action": action, "field": field},
                )
            unexpected_nested = sorted(set(map(str, nested_value)) - nested_allowed_fields)
            if unexpected_nested:
                return GuardrailDecision.block(
                    "ACTION_FIELDS_NOT_ALLOWED",
                    "structured action contains nested fields outside its contract",
                    _INVALID_PAYLOAD_MESSAGE,
                    details={
                        "action": action,
                        "field": field,
                        "fields": unexpected_nested,
                    },
                )
        return GuardrailDecision.allow()
