import json
import logging
import re
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig

from src.agents.state import AgentState
from src.agents.tools import search_knowledge, update_post_booking_signals
from src.agents.trace import message_to_log, messages_to_log, trace_async_operation, trace_event, trace_node
from src.agents.utils import get_system_prompt, window_messages
from src.dependencies import post_booking_signal_repair_queue, profile_service
from src.services.llm import extract_response_text, get_classifier_llm, get_llm

SKILL_PATH = Path(__file__).parent.parent / "skills" / "post_booking_skill" / "SKILL.md"
_FOLLOW_UPS_BLOCK = re.compile(r"<<<FOLLOW_UPS>>>\s*(\[.*?\])\s*<<<END_FOLLOW_UPS>>>", re.DOTALL)


def _extract_follow_ups(content: str) -> tuple[str, list[dict[str, str]]]:
    """Remove the model-only block and retain up to two exploration prompts."""
    match = _FOLLOW_UPS_BLOCK.search(content)
    visible_content = _FOLLOW_UPS_BLOCK.sub("", content).strip()
    if not match:
        return visible_content, []
    try:
        raw_items = json.loads(match.group(1))
    except json.JSONDecodeError:
        return visible_content, []
    if not isinstance(raw_items, list):
        return visible_content, []

    follow_ups: list[dict[str, str]] = []
    seen_texts: set[str] = set()
    for item in raw_items:
        text = " ".join(str(item).split()) if isinstance(item, str) else ""
        text_key = text.casefold()
        if not 1 <= len(text) <= 240 or text_key in seen_texts or "?" in text:
            continue
        follow_ups.append({"text": text})
        seen_texts.add(text_key)
        if len(follow_ups) == 2:
            break
    return visible_content, follow_ups


def get_post_booking_prompt() -> str:
    return SKILL_PATH.read_text(encoding="utf-8")


def _profile_signal_called_for_latest_user_turn(messages: Sequence[object]) -> bool:
    """Return whether the current user turn completed its mandatory signal call."""
    latest_user_index = next(
        (index for index in range(len(messages) - 1, -1, -1) if getattr(messages[index], "type", "") == "human"),
        None,
    )
    if latest_user_index is None:
        return False
    signal_call_ids: set[str] = set()
    for message in messages[latest_user_index + 1 :]:
        if not isinstance(message, AIMessage):
            if (
                isinstance(message, ToolMessage)
                and str(message.tool_call_id or "") in signal_call_ids
                and getattr(message, "status", "success") != "error"
            ):
                return True
            continue
        signal_call_ids.update(
            str(call.get("id") or "")
            for call in message.tool_calls or []
            if call.get("name") == update_post_booking_signals.name
        )
    return bool(signal_call_ids) and not any(
        isinstance(message, ToolMessage)
        and str(message.tool_call_id or "") in signal_call_ids
        and getattr(message, "status", "success") == "error"
        for message in messages[latest_user_index + 1 :]
    )


def _latest_signal_tool_error(messages: Sequence[object]) -> dict[str, object] | None:
    """Return the latest failed signal-tool payload for background diagnostics."""
    for message in reversed(messages):
        if not isinstance(message, ToolMessage) or getattr(message, "name", "") != update_post_booking_signals.name:
            continue
        if getattr(message, "status", "success") != "error":
            return None
        try:
            payload = json.loads(str(message.content))
        except (TypeError, json.JSONDecodeError):
            return {"raw": str(message.content)}
        return payload if isinstance(payload, dict) else {"raw": str(message.content)}
    return None


def _signal_tool_call(response: AIMessage) -> dict[str, Any] | None:
    call = next(
        (
            c
            for c in response.tool_calls or []
            if c.get("name") == update_post_booking_signals.name
        ),
        None,
    )
    return dict(call) if call is not None else None


def _signal_call_has_payload(call: dict[str, object] | None) -> bool:
    if not call:
        return False
    arguments = call.get("args") or {}
    if not isinstance(arguments, dict):
        return False
    return bool(arguments.get("profile_signals") or arguments.get("booking_signals"))


async def _repair_signal_tool_call(
    *,
    prompt: str,
    messages: Sequence[Any],
    trace_id: str,
    config: RunnableConfig | None,
) -> dict[str, Any] | None:
    """Retry structured extraction when the advisory model omitted its payload."""
    repair_llm = get_classifier_llm()
    if repair_llm is None:
        return None
    repair_prompt = (
        prompt
        + "\n\n--- SIGNAL EXTRACTION REPAIR ---\n"
        "Re-evaluate only the latest user message. Call update_post_booking_signals "
        "exactly once and return no prose. Use empty arrays only when that message "
        "truly contains no supported profile or booking fact. Apply the tool schema's "
        "scope, participant, correction, and non-inference rules exactly."
    )
    repaired = await trace_async_operation(
        "llm.post_booking_signal_inline_repair",
        trace_id=trace_id,
        input={"tool": update_post_booking_signals.name},
        awaitable=repair_llm.bind_tools(
            [update_post_booking_signals],
            tool_choice=update_post_booking_signals.name,
        ).ainvoke(
            [SystemMessage(content=repair_prompt), *window_messages(list(messages))],
            config=config,
        ),
    )
    return _signal_tool_call(repaired)


def _replace_signal_tool_call(
    response: AIMessage,
    repaired_call: dict[str, object],
) -> AIMessage:
    retained = [
        call
        for call in response.tool_calls or []
        if call.get("name") != update_post_booking_signals.name
    ]
    return response.model_copy(update={"tool_calls": [*retained, repaired_call]})


def _latest_user_turn_key(messages: Sequence[object]) -> str:
    for index in range(len(messages) - 1, -1, -1):
        message = messages[index]
        if getattr(message, "type", "") == "human":
            return str(getattr(message, "id", "") or index)
    return ""


def _llm_visible_messages(messages: Sequence[Any]) -> list[BaseMessage]:
    """Hide profile-persistence health from user-facing answer generation."""
    visible: list[BaseMessage] = []
    for message in window_messages(list(messages)):
        if isinstance(message, ToolMessage) and getattr(message, "name", "") == update_post_booking_signals.name:
            visible.append(message.model_copy(update={"content": '{"status":"accepted"}'}))
        else:
            visible.append(message)
    return visible


def _latest_knowledge_results(messages: Sequence[object]) -> list[dict[str, object]]:
    """Return decoded knowledge payloads belonging to the latest user turn."""
    latest_user_index = next(
        (index for index in range(len(messages) - 1, -1, -1) if getattr(messages[index], "type", "") == "human"),
        None,
    )
    if latest_user_index is None:
        return []
    results: list[dict[str, object]] = []
    for message in messages[latest_user_index + 1 :]:
        if not isinstance(message, ToolMessage) or getattr(message, "name", "") != search_knowledge.name:
            continue
        try:
            payload = json.loads(str(message.content))
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            results.append(payload)
    return results


def _no_knowledge_match_response() -> str:
    return (
        "ViVi chưa có nguồn dữ liệu đủ căn cứ để trả lời chính xác nội dung này. "
        "Quý khách nên xác nhận với tư vấn viên trong buổi lái thử hoặc nói rõ thêm mẫu xe, phiên bản, năm xe hay chính sách cần hỏi."
    )


def _last_user_text(messages: Sequence[object]) -> str:
    for message in reversed(messages):
        if getattr(message, "type", "") == "human":
            return str(getattr(message, "content", "")).strip()
    return ""


def _normalized_text(value: str) -> str:
    return re.sub(r"\W+", "", value, flags=re.UNICODE).casefold()


def _tool_call_prose_before(messages: Sequence[object]) -> str:
    """Recover prose emitted alongside a tool call when its continuation is empty."""
    for message in reversed(messages[:-1]):
        if isinstance(message, AIMessage) and getattr(message, "tool_calls", None):
            prose, _ = _extract_follow_ups(extract_response_text(message))
            return prose
    return ""


@trace_node("post_booking_skill")
async def post_booking_skill_node(state: AgentState, config: RunnableConfig | None = None) -> dict:
    diagnostic_started = time.perf_counter()
    messages = list(state.get("messages") or [])
    metadata = state.get("metadata") or {}
    trace_id = metadata.get("trace_id", "")
    booking_context = state.get("post_booking_context") or {"active": False}
    participant_context = state.get("participant_context") or {"role": "booker"}
    action_result = state.get("action_result")
    if isinstance(action_result, dict) and action_result.get("status") == "confirmed" and action_result.get("booking_id"):
        booking_context = {"active": True, **profile_service.booking_context(str(action_result["booking_id"]))}
        participant_context = profile_service.participant_context(str(action_result["booking_id"]), "booker")
    prompt = (
        f"{get_system_prompt()}\n\n--- ACTIVE SKILL GUIDELINES (POST BOOKING) ---\n{get_post_booking_prompt()}"
        f"\n\n--- USER PROFILE CONTEXT ---\n{json.dumps((state.get('profile_context') or {}).get('sections') or {}, ensure_ascii=False)}"
        f"\n\n--- BOOKING CONTEXT ---\n{json.dumps(booking_context, ensure_ascii=False)}"
        f"\n\n--- CURRENT PARTICIPANT ---\n{json.dumps(participant_context, ensure_ascii=False)}"
        "\n\nFor a driver invitation, you are speaking directly to the authenticated driver named in "
        "BOOKING CONTEXT.participants.driver. Use that identity and the booking details when relevant; "
        "never claim you do not know who the driver is."
    )
    prompt_build_ms = (time.perf_counter() - diagnostic_started) * 1000
    last = messages[-1] if messages else None
    if isinstance(last, ToolMessage):
        trace_event("tool.result", trace_id=trace_id, node="post_booking_skill", tool_message=message_to_log(last))
    knowledge_results = _latest_knowledge_results(messages)
    if (
        knowledge_results
        and all(not result.get("facts") for result in knowledge_results)
        and _profile_signal_called_for_latest_user_turn(messages)
    ):
        response_text = _no_knowledge_match_response()
        response = AIMessage(content=response_text)
        return {
            "messages": [response],
            "response": response_text,
            "active_skill": "post_booking",
            "post_booking_context": booking_context,
            "metadata": metadata,
        }
    try:
        llm = get_llm()
        if llm is None:
            query = str(state.get("query") or "")
            grounded = json.loads(
                search_knowledge.invoke(
                    {"query": query, "model_code": str(booking_context.get("model_code") or "")}, config=config
                )
            )
            facts = grounded.get("facts") or []
            text = facts[0]["content"] if facts else "ViVi có thể giúp bạn chuẩn bị checklist lái thử, đánh giá pin/sạc, ADAS, không gian gia đình và các câu hỏi nên trao đổi với tư vấn viên."
            response = AIMessage(content=text)
        else:
            signal_already_called = _profile_signal_called_for_latest_user_turn(messages)
            bind_tools_started = time.perf_counter()
            bound = llm.bind_tools([search_knowledge, update_post_booking_signals])
            bind_tools_ms = (time.perf_counter() - bind_tools_started) * 1000
            continuation_instruction = ""
            if isinstance(last, ToolMessage):
                continuation_instruction = (
                    "\n\nThe tool result has just been received. Your earlier draft was not sent to the user. "
                    "Now return one complete user-visible answer: useful information, a practical recommendation, "
                    "and only then any eligible follow-up transport block. Never return only the transport block. "
                    "Never mention profile-signal queueing, persistence, or failure status to the user."
                )
            if any(not result.get("facts") for result in knowledge_results):
                continuation_instruction += (
                    "\n\nAt least one knowledge lookup returned no matching evidence. State clearly that ViVi does not "
                    "have verified information for that scope, and ask the customer to confirm with the showroom or "
                    "clarify the model, trim, year, market, or policy. Never fill that gap with a guess."
                )
            visible_messages_started = time.perf_counter()
            llm_messages = [SystemMessage(content=prompt + continuation_instruction)] + _llm_visible_messages(messages)
            visible_messages_ms = (time.perf_counter() - visible_messages_started) * 1000
            llm_request_log_started = time.perf_counter()
            trace_event("llm.request", trace_id=trace_id, node="post_booking_skill", messages=messages_to_log(llm_messages), tools=[search_knowledge.name, update_post_booking_signals.name])
            trace_event(
                "diagnostic.post_booking_pre_invoke",
                trace_id=trace_id,
                prompt_build_ms=round(prompt_build_ms, 2),
                bind_tools_ms=round(bind_tools_ms, 2),
                visible_messages_ms=round(visible_messages_ms, 2),
                llm_request_log_ms=round((time.perf_counter() - llm_request_log_started) * 1000, 2),
                state_message_count=len(messages),
                llm_message_count=len(llm_messages),
                prompt_chars=len(prompt),
                llm_message_content_chars=sum(len(str(getattr(message, "content", ""))) for message in llm_messages),
            )
            response = await trace_async_operation(
                "llm.post_booking_skill",
                trace_id=trace_id,
                input={
                    "messages": messages_to_log(llm_messages),
                    "tools": [search_knowledge.name, update_post_booking_signals.name],
                },
                awaitable=bound.ainvoke(llm_messages, config=config),
            )
            signal_call = _signal_tool_call(response)
            response_has_signal_call = signal_call is not None
            repair_turn_key = _latest_user_turn_key(messages)
            repaired_inline = False
            if not signal_already_called and not _signal_call_has_payload(signal_call):
                try:
                    repaired_call = await _repair_signal_tool_call(
                        prompt=prompt,
                        messages=messages,
                        trace_id=str(trace_id),
                        config=config,
                    )
                except Exception:
                    logging.getLogger(__name__).exception(
                        "Inline post-booking signal repair failed"
                    )
                    repaired_call = None
                if repaired_call is not None:
                    response = _replace_signal_tool_call(response, repaired_call)
                    response_has_signal_call = True
                    repaired_inline = True
                    trace_event(
                        "post_booking_signal_repair.inline_completed",
                        trace_id=str(trace_id),
                        payload_present=_signal_call_has_payload(repaired_call),
                    )
            if (
                not signal_already_called
                and (not response_has_signal_call or not repaired_inline)
                and not _signal_call_has_payload(_signal_tool_call(response))
                and metadata.get("post_booking_signal_repair_turn") != repair_turn_key
            ):
                prior_tool_error = _latest_signal_tool_error(messages)
                reason = "tool_failed" if prior_tool_error else "signal_call_omitted"
                metadata = {**metadata, "post_booking_signal_repair_turn": repair_turn_key}
                await post_booking_signal_repair_queue.enqueue(
                    trace_id=str(trace_id),
                    conversation_id=str(metadata.get("conversation_id") or ""),
                    profile_id=str(state.get("profile_id") or ""),
                    user_message=_last_user_text(messages),
                    profile_sections=dict((state.get("profile_context") or {}).get("sections") or {}),
                    booking_context=booking_context,
                    participant_context=participant_context,
                    reason=reason,
                    prior_tool_error=prior_tool_error,
                )
    except Exception as exc:
        logging.getLogger(__name__).exception("Post booking skill failed")
        response = AIMessage(content="ViVi chưa lấy được nguồn thông tin phù hợp lúc này. Bạn có thể hỏi về checklist lái thử, pin/sạc, ADAS hoặc không gian sử dụng.")
        return {"messages": [response], "response": response.content, "error": str(exc), "active_skill": "post_booking", "metadata": metadata}
    content = extract_response_text(response)
    calls = bool(getattr(response, "tool_calls", None))
    visible_content, follow_ups = _extract_follow_ups(content)
    if not calls and not visible_content and isinstance(last, ToolMessage):
        visible_content = _tool_call_prose_before(messages)
        if visible_content:
            response = AIMessage(content=visible_content)

    last_user_text = _last_user_text(messages)
    if (
        not calls
        and llm is not None
        and (
            not visible_content
            or _normalized_text(visible_content) == _normalized_text(last_user_text)
        )
    ):
        repair_messages = [
            SystemMessage(
                content=(
                    prompt
                    + "\n\nReturn a complete post-booking advisory answer to the latest user message. "
                    "The previous draft merely repeated the user's words and must not be shown. "
                    "Do not call tools in this repair response."
                )
            ),
            *window_messages(messages),
        ]
        response = await trace_async_operation(
            "llm.post_booking_skill_repair",
            trace_id=trace_id,
            input={"messages": messages_to_log(repair_messages)},
            awaitable=llm.ainvoke(repair_messages, config=config),
        )
        content = extract_response_text(response)
        visible_content, follow_ups = _extract_follow_ups(content)
        if not visible_content:
            visible_content = "ViVi cần thêm một chút thông tin về nhu cầu sử dụng để gợi ý đúng các bài kiểm tra cho buổi lái thử."
            response = AIMessage(content=visible_content)
    if not calls and visible_content != content:
        # Do not retain transport instructions in the conversation history.
        response = AIMessage(content=visible_content)
    result = {"messages": [response], "response": visible_content, "active_skill": "post_booking", "post_booking_context": booking_context, "tool_call_count": (state.get("tool_call_count") or 0) + (1 if calls else 0), "metadata": metadata}
    # Tool-call turns are intermediate graph turns, never a completed response.
    if not calls:
        result["follow_ups"] = follow_ups
    return result
