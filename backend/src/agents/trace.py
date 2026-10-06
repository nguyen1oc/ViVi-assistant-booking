from __future__ import annotations

import json
import logging
import os
import re
import time
from collections.abc import Awaitable, Callable, Mapping, Sequence
from functools import wraps
from typing import Any, TypeVar

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langsmith import traceable

from src.guardrails.policies import PUBLIC_TOOL_INPUT_SECRET_KEYS, SECRET_VALUE_KEYS, is_sensitive_key

LOGGER_NAME = "ai_agent"
_T = TypeVar("_T")

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
_SECRET_KEYS = SECRET_VALUE_KEYS | PUBLIC_TOOL_INPUT_SECRET_KEYS


def _mask_text(value: str, *, limit: int = 4000) -> str:
    masked = _EMAIL_RE.sub("[email]", value)
    masked = _PHONE_RE.sub("[phone]", masked)
    masked = _CREDENTIAL_ASSIGNMENT_RE.sub(lambda match: f"{match.group(1)}=[redacted]", masked)
    masked = _STANDALONE_SECRET_RE.sub("[redacted]", masked)
    masked = _VIETNAM_ID_RE.sub("[personal-id]", masked)
    return masked if len(masked) <= limit else masked[:limit] + "...[truncated]"


def redact(value: Any, *, key: str = "") -> Any:
    if is_sensitive_key(key, _SECRET_KEYS):
        return "[redacted]"
    if isinstance(value, str):
        return _mask_text(value)
    if isinstance(value, Mapping):
        return {str(k): redact(v, key=str(k)) for k, v in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [redact(item) for item in value]
    return value


def message_to_log(message: BaseMessage) -> dict[str, Any]:
    data: dict[str, Any] = {
        "type": message.__class__.__name__,
        "content": redact(getattr(message, "content", "")),
    }
    if isinstance(message, AIMessage) and message.tool_calls:
        data["tool_calls"] = redact(message.tool_calls)
    if isinstance(message, ToolMessage):
        data.update(
            {
                "name": message.name,
                "tool_call_id": message.tool_call_id,
                "status": getattr(message, "status", "success"),
            }
        )
    if isinstance(message, (HumanMessage, SystemMessage)):
        data["role"] = message.type
    return data


def messages_to_log(messages: Sequence[BaseMessage]) -> list[dict[str, Any]]:
    return [message_to_log(message) for message in messages]


def trace_event(event: str, **fields: Any) -> None:
    payload = {"event": event, **redact(fields)}
    logging.getLogger(LOGGER_NAME).info(json.dumps(payload, ensure_ascii=False, default=str))
    _publish_langsmith_event(event, payload)


def _publish_langsmith_event(event: str, payload: dict[str, Any]) -> None:
    """Mirror structured local events to LangSmith as optional nested spans."""
    if os.getenv("LANGSMITH_EVENT_LOGS", "false").casefold() not in {"1", "true", "yes", "on"}:
        return

    @traceable(
        name=f"event.{event}",
        run_type="chain",
        process_inputs=redact,
        process_outputs=redact,
    )
    def record_event(event_payload: dict[str, Any]) -> dict[str, Any]:
        return {"recorded": True, "event": event_payload["event"]}

    try:
        record_event(payload)
    except Exception:
        # Observability must never affect the chat/booking path.
        logging.getLogger(LOGGER_NAME).debug("Unable to mirror event to LangSmith", exc_info=True)


def error_details(exc: Exception) -> dict[str, str]:
    """Return a stable, safe error shape for trace events."""
    code = str(getattr(exc, "code", "") or type(exc).__name__.upper())
    return {
        "error_code": code,
        "error_type": type(exc).__name__,
        "error_message": str(exc),
    }


def state_snapshot(state: Mapping[str, Any]) -> dict[str, Any]:
    """Keep node traces useful without serialising the complete graph state."""
    keys = (
        "query",
        "context",
        "requested_action",
        "action_payload",
        "intent",
        "active_skill",
        "action_tool",
        "action_input",
        "action_result",
        "action_error",
        "response",
        "tool_call_count",
    )
    snapshot = {key: state[key] for key in keys if key in state and state[key] is not None}
    messages = state.get("messages")
    if isinstance(messages, Sequence) and not isinstance(messages, (str, bytes, bytearray)):
        snapshot["messages"] = [message_to_log(item) if isinstance(item, BaseMessage) else redact(item) for item in messages]
    return redact(snapshot)


def trace_node(node: str) -> Callable[[Callable[..., Awaitable[dict[str, Any]]]], Callable[..., Awaitable[dict[str, Any]]]]:
    """Emit input, output, latency and failures around an async LangGraph node."""
    def decorator(func: Callable[..., Awaitable[dict[str, Any]]]) -> Callable[..., Awaitable[dict[str, Any]]]:
        @wraps(func)
        async def wrapped(state: Mapping[str, Any], *args: Any, **kwargs: Any) -> dict[str, Any]:
            trace_id = str((state.get("metadata") or {}).get("trace_id") or "")
            started = time.perf_counter()
            snapshot_started = time.perf_counter()
            input_snapshot = state_snapshot(state)
            snapshot_ms = (time.perf_counter() - snapshot_started) * 1000
            serialization_started = time.perf_counter()
            input_log_bytes = len(json.dumps(input_snapshot, ensure_ascii=False, default=str).encode("utf-8"))
            serialization_ms = (time.perf_counter() - serialization_started) * 1000
            node_started_log_started = time.perf_counter()
            trace_event(
                "node.started",
                trace_id=trace_id,
                node=node,
                input=input_snapshot,
                diagnostic={
                    "snapshot_ms": round(snapshot_ms, 2),
                    "input_json_ms": round(serialization_ms, 2),
                    "input_log_bytes": input_log_bytes,
                    "message_count": len(state.get("messages") or []),
                },
            )
            trace_event(
                "diagnostic.node_input_trace",
                trace_id=trace_id,
                node=node,
                node_started_log_ms=round((time.perf_counter() - node_started_log_started) * 1000, 2),
            )
            try:
                output = await func(state, *args, **kwargs)
            except Exception as exc:
                trace_event(
                    "node.failed",
                    trace_id=trace_id,
                    node=node,
                    latency_ms=round((time.perf_counter() - started) * 1000, 2),
                    **error_details(exc),
                )
                raise
            trace_event(
                "node.completed",
                trace_id=trace_id,
                node=node,
                latency_ms=round((time.perf_counter() - started) * 1000, 2),
                status="error" if output.get("action_error") or output.get("error") else "success",
                output=state_snapshot(output),
            )
            return output
        return wrapped
    return decorator


async def trace_async_operation(
    operation: str,
    *,
    trace_id: str,
    input: Any,
    awaitable: Awaitable[_T],
) -> _T:
    """Trace one awaited dependency call, such as an LLM invocation."""
    started = time.perf_counter()
    operation_started_log_started = time.perf_counter()
    trace_event("operation.started", trace_id=trace_id, operation=operation, input=input)
    trace_event(
        "diagnostic.operation_input_trace",
        trace_id=trace_id,
        operation=operation,
        operation_started_log_ms=round((time.perf_counter() - operation_started_log_started) * 1000, 2),
    )
    try:
        output = await awaitable
    except Exception as exc:
        trace_event(
            "operation.failed",
            trace_id=trace_id,
            operation=operation,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
            **error_details(exc),
        )
        raise
    trace_event(
        "operation.completed",
        trace_id=trace_id,
        operation=operation,
        latency_ms=round((time.perf_counter() - started) * 1000, 2),
        output=message_to_log(output) if isinstance(output, BaseMessage) else output,
    )
    return output
