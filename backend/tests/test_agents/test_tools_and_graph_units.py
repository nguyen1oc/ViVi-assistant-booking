import pytest
from langchain_core.messages import AIMessage
from src.agents.graph import MAX_TOOL_CALLS, route_intent, should_continue_booking


# test case of Chau + kiểm tra route_intent chọn đúng node theo intent và fallback domain
@pytest.mark.parametrize(
    ("state", "expected"),
    [
        ({"intent": "sensitive"}, "sensitive_policy"),
        ({"intent": "domain", "active_skill": "booking"}, "booking_skill"),
        ({"intent": "domain", "active_skill": "advise"}, "booking_skill"),
        ({"intent": "domain"}, "booking_skill"),
        ({}, "booking_skill"),
        ({"intent": "unknown"}, "booking_skill"),
    ],
)
def test_route_intent_mapping(state, expected):
    assert route_intent(state) == expected


# test case of Chau + kiểm tra skill chỉ gọi tool khi có tool call và chưa vượt loop limit
def test_should_continue_booking_respects_tool_calls_and_loop_limit():
    tool_message = AIMessage(
        content="",
        tool_calls=[{"id": "call-1", "name": "search_knowledge", "args": {"query": "VF6"}}],
    )

    assert should_continue_booking({"messages": []}) == "end"
    assert should_continue_booking({"messages": [AIMessage(content="done")]}) == "end"
    assert should_continue_booking({"messages": [tool_message], "tool_call_count": 0}) == "continue"
    assert should_continue_booking({"messages": [tool_message], "tool_call_count": MAX_TOOL_CALLS}) == "max_tool_limit"


@pytest.mark.asyncio
async def test_max_tool_limit_node_cleans_dangling_tool_calls():
    from src.agents.graph import max_tool_limit_node

    tool_message = AIMessage(
        content="",
        tool_calls=[{"id": "call-1", "name": "search_knowledge", "args": {"query": "VF6"}}],
    )
    result = await max_tool_limit_node({"messages": [tool_message], "tool_call_count": MAX_TOOL_CALLS})
    assert result["action_error"] == "MAX_TOOL_CALLS_EXCEEDED"
    assert len(result["messages"]) == 2
    assert result["messages"][0].status == "error"
    assert result["messages"][0].tool_call_id == "call-1"
    assert isinstance(result["messages"][1], AIMessage)
