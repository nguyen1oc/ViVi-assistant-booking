import json
import logging
from collections.abc import Collection, Mapping
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import ToolNode
from pydantic import ValidationError

from src.agents.trace import error_details, trace_event, trace_node
from src.config import Settings, get_settings
from src.guardrails.models import GuardrailDecision
from src.guardrails.policies import (
    CONFIRMATION_ACTION_BY_TOOL,
    CONFIRMATION_BOUND_FIELDS_BY_TOOL,
    CONFIRMATION_TOOL_NAMES,
    MUTATING_TOOL_NAMES,
)
from src.guardrails.structure import PayloadLimits, validate_payload
from src.services.booking.errors import BookingError

_TOOL_BLOCKED_MESSAGE = "Thao tác này đã bị chặn bởi chính sách an toàn. Vui lòng kiểm tra và thử lại."


def _has_bound_structured_confirmation(state: dict[str, Any], tool_name: str, arguments: Mapping[str, Any]) -> bool:
    expected_action = CONFIRMATION_ACTION_BY_TOOL.get(tool_name)
    bound_fields = CONFIRMATION_BOUND_FIELDS_BY_TOOL.get(tool_name, frozenset())
    payload = state.get("action_payload")
    if state.get("requested_action") != expected_action or not isinstance(payload, Mapping):
        return False
    if not bound_fields.issubset(payload) or not bound_fields.issubset(arguments):
        return False
    return all(payload[field] == arguments[field] for field in bound_fields)


def serialize_tool_error(error: Exception) -> str:
    """Preserve safe domain error details so the agent can clarify naturally."""
    logging.getLogger("tool.execution").exception("tool_execution_failed %s", error_details(error))
    if isinstance(error, BookingError):
        return json.dumps(
            {
                "error": {
                    "code": error.code,
                    "message": str(error),
                    "retryable": error.retryable,
                }
            },
            ensure_ascii=False,
        )
    if isinstance(error, ValidationError):
        return json.dumps(
            {
                "error": {
                    "code": "TOOL_VALIDATION_FAILED",
                    "message": "Dữ liệu thao tác chưa hợp lệ.",
                    "retryable": False,
                    "fields": [str(item.get("loc", "")) for item in error.errors()],
                }
            },
            ensure_ascii=False,
        )
    return json.dumps(
        {
            "error": {
                "code": "TOOL_EXECUTION_FAILED",
                "message": "Thao tác chưa thể hoàn tất lúc này. Quý khách vui lòng thử lại.",
                "retryable": True,
            }
        },
        ensure_ascii=False,
    )


def inspect_tool_calls(
    state: dict[str, Any],
    *,
    allowed_tool_names: Collection[str],
    settings: Settings,
) -> GuardrailDecision:
    messages = state.get("messages") or []
    last_message = messages[-1] if messages else None
    if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
        return GuardrailDecision.block(
            "INVALID_TOOL_STATE",
            "tool node invoked without an AIMessage containing tool calls",
            _TOOL_BLOCKED_MESSAGE,
        )

    calls = last_message.tool_calls
    if len(calls) > settings.guardrails_max_tool_calls_per_message:
        return GuardrailDecision.block(
            "TOOL_CALL_LIMIT_EXCEEDED",
            "model requested too many tools in one message",
            _TOOL_BLOCKED_MESSAGE,
            details={"count": len(calls)},
        )

    limits = PayloadLimits(
        max_bytes=settings.guardrails_max_payload_bytes,
        max_depth=settings.guardrails_max_payload_depth,
        max_nodes=settings.guardrails_max_payload_nodes,
        max_string_chars=settings.guardrails_max_payload_string_chars,
    )
    allowed = set(allowed_tool_names)
    fingerprints: set[str] = set()
    mutating_calls = 0
    for call in calls:
        name = str(call.get("name") or "")
        arguments = call.get("args")
        if name not in allowed:
            return GuardrailDecision.block(
                "TOOL_NOT_ALLOWED",
                f"tool is outside the active skill allowlist: {name}",
                _TOOL_BLOCKED_MESSAGE,
                details={"tool": name},
            )
        if not isinstance(arguments, dict):
            return GuardrailDecision.block(
                "INVALID_TOOL_ARGUMENTS",
                f"tool arguments are not an object: {name}",
                _TOOL_BLOCKED_MESSAGE,
                details={"tool": name},
            )
        violation = validate_payload(arguments, limits)
        if violation:
            return GuardrailDecision.block(
                "TOOL_PAYLOAD_LIMIT_EXCEEDED",
                f"{name}: {violation}",
                _TOOL_BLOCKED_MESSAGE,
                details={"tool": name},
            )
        canonical = json.dumps({"name": name, "args": arguments}, sort_keys=True, default=str)
        if canonical in fingerprints:
            return GuardrailDecision.block(
                "DUPLICATE_TOOL_CALL",
                f"duplicate tool call in one model message: {name}",
                _TOOL_BLOCKED_MESSAGE,
                details={"tool": name},
            )
        fingerprints.add(canonical)
        mutating_calls += int(name in MUTATING_TOOL_NAMES)

        if name in CONFIRMATION_TOOL_NAMES and not _has_bound_structured_confirmation(state, name, arguments):
            return GuardrailDecision.block(
                "EXPLICIT_CONFIRMATION_REQUIRED",
                "confirmation tool call is not bound to the matching structured action and payload",
                "Vui lòng dùng nút xác nhận để chốt đúng lịch lái thử đang hiển thị.",
                details={"tool": name},
            )

    if mutating_calls > 1 or (mutating_calls and len(calls) > 1):
        return GuardrailDecision.block(
            "MUTATION_BATCH_NOT_ALLOWED",
            "mutating tools must execute one at a time",
            _TOOL_BLOCKED_MESSAGE,
            details={"mutating_calls": mutating_calls, "total_calls": len(calls)},
        )
    return GuardrailDecision.allow()


def build_guarded_tool_node(tools: list[Any], *, skill_name: str):
    """Wrap LangGraph's ToolNode with deterministic pre-execution checks."""
    base_node = ToolNode(tools, handle_tool_errors=serialize_tool_error)
    allowed_tool_names = {tool.name for tool in tools}

    @trace_node(f"{skill_name}.tools")
    async def guarded_tool_node(
        state: dict[str, Any], config: RunnableConfig | None = None
    ) -> dict[str, Any]:
        settings = get_settings()
        if not settings.guardrails_enabled:
            return await base_node.ainvoke(state, config=config)
        decision = inspect_tool_calls(
            state,
            allowed_tool_names=allowed_tool_names,
            settings=settings,
        )
        if decision.allowed:
            result = await base_node.ainvoke(state, config=config)
            trace_id = str((state.get("metadata") or {}).get("trace_id") or "")
            for message in result.get("messages") or []:
                if isinstance(message, ToolMessage) and getattr(message, "status", "success") == "error":
                    trace_event(
                        "tool.failed",
                        trace_id=trace_id,
                        skill=skill_name,
                        tool=message.name,
                        tool_call_id=message.tool_call_id,
                        error=message.content,
                    )
            return result

        messages = state.get("messages") or []
        last_message = messages[-1] if messages else None
        blocked_messages: list[ToolMessage] = []
        if isinstance(last_message, AIMessage):
            for call in last_message.tool_calls:
                blocked_messages.append(
                    ToolMessage(
                        content=json.dumps(
                            {
                                "error": {
                                    "code": decision.code,
                                    "message": decision.user_message,
                                    "tool": str(call.get("name") or "unknown"),
                                }
                            },
                            ensure_ascii=False,
                        ),
                        tool_call_id=str(call.get("id") or "guardrail-blocked"),
                        name=str(call.get("name") or "unknown"),
                        status="error",
                    )
                )
        return {
            "messages": blocked_messages,
            "action_error": decision.code,
            "metadata": {
                **(state.get("metadata") or {}),
                "guardrail": {"code": decision.code, "skill": skill_name},
            },
        }

    return guarded_tool_node
