import logging
from pathlib import Path
from typing import Any

from langchain_core.messages import SystemMessage, ToolMessage

from src.agents.constants import (
    PUBLIC_LLM_UNAVAILABLE_CODE,
    PUBLIC_LLM_UNAVAILABLE_MESSAGE,
)
from src.agents.state import AgentState
from src.agents.tools import search_knowledge
from src.agents.trace import message_to_log, messages_to_log, trace_event
from src.agents.utils import get_system_prompt, window_messages
from src.dependencies import usage_budget_service
from src.guardrails.untrusted_content import protect_tool_result_messages
from src.services.llm import extract_response_text, get_llm
from src.services.usage_budget import (
    BudgetExceededError,
    LLMCallLimitExceededError,
    invoke_with_budget,
)

SKILL_PATH = Path(__file__).parent.parent / "skills" / "advise_skill" / "SKILL.md"


def get_advise_prompt() -> str:
    try:
        with open(SKILL_PATH, encoding="utf-8") as f:
            return f.read()
    except Exception:
        return "You are the Advisory Assistant. Help users explore VinFast electric vehicle models, specs, range, pricing, and features."


async def advise_skill_node(state: AgentState) -> dict:
    messages = list(state.get("messages") or [])
    metadata = state.get("metadata") or {}
    trace_id = metadata.get("trace_id", "")
    last_message = messages[-1] if messages else None
    if isinstance(last_message, ToolMessage):
        trace_event(
            "tool.result",
            trace_id=trace_id,
            node="advise_skill",
            tool_message=message_to_log(last_message),
            failed=getattr(last_message, "status", "success") == "error",
        )

    prompt = f"{get_system_prompt()}\n\n--- ACTIVE SKILL GUIDELINES (ADVISE) ---\n{get_advise_prompt()}"

    tools = [search_knowledge]

    try:
        llm = get_llm()
        if llm is None:
            raise RuntimeError("LLM is not configured")
        llm_with_tools = llm.bind_tools(tools)
        safe_history = protect_tool_result_messages(window_messages(messages))
        llm_messages = [SystemMessage(content=prompt), *safe_history]
        trace_event(
            "llm.request",
            trace_id=trace_id,
            node="advise_skill",
            tools=[tool.name for tool in tools],
            messages=messages_to_log(llm_messages),
        )
        response = await invoke_with_budget(
            llm_with_tools,
            llm_messages,
            model=getattr(llm, "model_name", "") or "chat",
            metadata=metadata,
            budget=usage_budget_service,
            call_purpose="advise_skill",
        )
    except (BudgetExceededError, LLMCallLimitExceededError) as e:
        from langchain_core.messages import AIMessage

        internal_error_code = (
            "LLM_BUDGET_EXCEEDED" if isinstance(e, BudgetExceededError) else "LLM_CALL_LIMIT_EXCEEDED"
        )
        trace_event("llm.limit", trace_id=trace_id, node="advise_skill", error_code=internal_error_code)
        safe_response = AIMessage(content=PUBLIC_LLM_UNAVAILABLE_MESSAGE)
        return {
            "messages": [safe_response],
            "response": safe_response.content,
            "action_error": PUBLIC_LLM_UNAVAILABLE_CODE,
            "metadata": metadata,
        }
    except Exception as e:
        trace_event("llm.error", trace_id=trace_id, node="advise_skill", error=str(e))
        logging.getLogger(__name__).exception("Error in advise_skill_node")
        from langchain_core.messages import AIMessage

        safe_response = AIMessage(
            content="ViVi chưa xử lý được yêu cầu này lúc này. Bạn vui lòng thử lại hoặc chọn trực tiếp từ bảng hỗ trợ bên trái giúp ViVi nhé."
        )
        return {
            "messages": [safe_response],
            "response": safe_response.content,
            "error": str(e),
            "metadata": metadata,
        }

    # Extract response text for the API
    response_content = extract_response_text(response)

    # Tăng tool_call_count nếu LLM đang gọi tool
    has_tool_calls = hasattr(response, "tool_calls") and bool(response.tool_calls)
    current_count = state.get("tool_call_count") or 0
    trace_event(
        "llm.response",
        trace_id=trace_id,
        node="advise_skill",
        message=message_to_log(response),
        has_tool_calls=has_tool_calls,
    )
    if has_tool_calls:
        for tool_call in response.tool_calls:
            trace_event(
                "tool.call",
                trace_id=trace_id,
                node="advise_skill",
                source="llm",
                tool=tool_call.get("name"),
                args=tool_call.get("args"),
                tool_call_id=tool_call.get("id"),
            )

    output: dict[str, Any] = {
        "messages": [response],
        "tool_call_count": current_count + 1 if has_tool_calls else current_count,
        "metadata": metadata,
    }
    if response_content:
        output["response"] = response_content

    return output
