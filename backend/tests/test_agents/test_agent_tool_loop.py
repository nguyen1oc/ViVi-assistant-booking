from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage, ToolMessage
from src.agents.graph import agent
from src.agents.nodes import booking_skill_node as booking_module
from src.agents.nodes.classifier_node import classifier_node
from src.agents.tools.search_test_drive_options import tool as search_options_module


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _scripted_tool_llm(*responses):
    bound = MagicMock()
    bound.ainvoke = AsyncMock(side_effect=responses)
    llm = MagicMock()
    llm.model_name = "test-chat-model"
    llm.bind_tools.return_value = bound
    return llm, bound


# Kiểm tra booking agent chạy đủ vòng gọi tool rồi trả câu trả lời bám tool result.
@pytest.mark.asyncio
async def test_booking_agent_executes_tool_and_returns_final_response(monkeypatch):
    tool_call = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "search_test_drive_options",
                "args": {"vehicle_model": "VF8"},
                "id": "call-search-options",
                "type": "tool_call",
            }
        ],
    )
    llm, bound = _scripted_tool_llm(tool_call, AIMessage(content="VF8 information found"))
    monkeypatch.setattr(booking_module, "get_llm", lambda: llm)
    monkeypatch.setattr(
        search_options_module.booking_service,
        "search_options",
        lambda **kwargs: {"vehicle_model": kwargs["vehicle_model"], "search_stage": "showroom_selection"},
    )

    result = await agent.ainvoke({"query": "Tìm lịch lái thử VF8"}, config=_config("booking-agent-real-tool-loop"))

    assert result["active_skill"] == "booking"
    assert result["response"].startswith("Đã chọn VF8")
    assert "cung cấp tỉnh, thành phố hoặc vị trí" in result["response"]
    assert result["tool_call_count"] == 1
    tool_messages = [message for message in result["messages"] if isinstance(message, ToolMessage)]
    assert len(tool_messages) == 1
    assert "VF8" in tool_messages[0].content
    assert bound.ainvoke.await_count == 1


# Kiểm tra booking agent chặn tool ngoài whitelist.
@pytest.mark.asyncio
async def test_booking_agent_converts_unauthorized_tool_call_to_tool_error(monkeypatch):
    unauthorized_call = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "search_knowledge",
                "args": {"query": "VF8 range"},
                "id": "call-unauthorized-tool",
                "type": "tool_call",
            }
        ],
    )
    llm, _ = _scripted_tool_llm(
        unauthorized_call,
        AIMessage(content="I cannot use that tool from booking skill"),
    )
    monkeypatch.setattr(booking_module, "get_llm", lambda: llm)

    result = await agent.ainvoke({"query": "Tìm lịch VF8"}, config=_config("booking-agent-tool-whitelist"))

    tool_messages = [message for message in result["messages"] if isinstance(message, ToolMessage)]
    assert len(tool_messages) == 1
    assert tool_messages[0].status == "error"
    assert "search_knowledge" in tool_messages[0].content
    assert result["response"] == "I cannot use that tool from booking skill"


# Kiểm tra lỗi LLM trong booking skill không làm toàn bộ API agent thất bại.
@pytest.mark.asyncio
async def test_booking_agent_handles_llm_exception_with_safe_response(monkeypatch):
    llm, _ = _scripted_tool_llm(RuntimeError("LLM unavailable"))
    monkeypatch.setattr(booking_module, "get_llm", lambda: llm)

    result = await agent.ainvoke({"query": "VF8 specifications"}, config=_config("chau-agent-llm-failure"))

    assert result["response"]
    assert "error" in result or "thử lại" in result["response"].lower()


# test case of Chau + kiểm tra bộ đếm tool được reset ở đầu mỗi user turn thay vì cộng dồn cả conversation
@pytest.mark.asyncio
async def test_classifier_resets_tool_call_counter_for_new_user_turn():

    result = await classifier_node({"query": "VF8 range", "tool_call_count": 8})

    assert result["tool_call_count"] == 0
