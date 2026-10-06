from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class GuardrailDecision:
    """Result of a deterministic guardrail check.

    ``reason`` and ``details`` are operational metadata. They may be logged after
    redaction, but must not be returned directly to a public client.
    """

    allowed: bool
    code: str = "ALLOW"
    reason: str = ""
    user_message: str = ""
    sanitized_text: str | None = None
    sanitized_context: dict[str, Any] | None = None
    details: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def allow(
        cls,
        *,
        sanitized_text: str | None = None,
        sanitized_context: dict[str, Any] | None = None,
    ) -> GuardrailDecision:
        return cls(
            allowed=True,
            sanitized_text=sanitized_text,
            sanitized_context=sanitized_context,
        )

    @classmethod
    def block(
        cls,
        code: str,
        reason: str,
        user_message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> GuardrailDecision:
        return cls(
            allowed=False,
            code=code,
            reason=reason,
            user_message=user_message,
            details=details or {},
        )


@dataclass(frozen=True, slots=True)
class ProtectedOutput:
    response: str
    analysis: str
    tool_input: dict[str, Any]
    action_data: Any | None
    action_error: str
