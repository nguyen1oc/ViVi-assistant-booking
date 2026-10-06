from __future__ import annotations

from functools import lru_cache
from typing import Any

from src.config import Settings, get_settings
from src.guardrails.input_guard import InputGuard
from src.guardrails.models import GuardrailDecision, ProtectedOutput
from src.guardrails.output_guard import OutputGuard
from src.guardrails.policies import DEMO_ACTION_ALLOWED_FIELDS, DEMO_ACTION_NESTED_ALLOWED_FIELDS
from src.guardrails.structure import PayloadLimits


class Guardrails:
    """Facade used by API routes.

    Prompt instructions remain useful for model behavior, but this class is the
    deterministic enforcement boundary and does not call an LLM.
    """

    def __init__(self, settings: Settings) -> None:
        self.enabled = settings.guardrails_enabled
        limits = PayloadLimits(
            max_bytes=settings.guardrails_max_payload_bytes,
            max_depth=settings.guardrails_max_payload_depth,
            max_nodes=settings.guardrails_max_payload_nodes,
            max_string_chars=settings.guardrails_max_payload_string_chars,
        )
        self.input = InputGuard(limits)
        self.output = OutputGuard(max_output_chars=settings.guardrails_max_output_chars)

    def inspect_input(
        self,
        *,
        message: str,
        conversation_id: str,
        context: dict[str, Any],
        action: str | None,
        action_payload: dict[str, Any],
    ) -> GuardrailDecision:
        if not self.enabled:
            return GuardrailDecision.allow(sanitized_text=message, sanitized_context=context)
        return self.input.inspect(
            message=message,
            conversation_id=conversation_id,
            context=context,
            action=action,
            action_payload=action_payload,
        )

    def protect_output(self, result: dict[str, Any]) -> ProtectedOutput:
        if not self.enabled:
            return ProtectedOutput(
                response=str(result.get("response", "")),
                analysis=str(result.get("analysis", "")),
                tool_input=result.get("action_input") or {},
                action_data=result.get("action_result"),
                action_error=str(result.get("action_error", "")),
            )
        return self.output.protect(result)

    def inspect_demo_action(self, *, action: str, payload: dict[str, Any]) -> GuardrailDecision:
        if not self.enabled:
            return GuardrailDecision.allow()
        return self.input.inspect_structured_payload(
            action=action,
            payload=payload,
            contracts=DEMO_ACTION_ALLOWED_FIELDS,
            nested_contracts=DEMO_ACTION_NESTED_ALLOWED_FIELDS,
        )


@lru_cache
def get_guardrails() -> Guardrails:
    return Guardrails(get_settings())
