from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import END, StateGraph
from src.agents.state import AgentState
from src.config import Settings
from src.guardrails.tool_guard import build_guarded_tool_node, inspect_tool_calls, serialize_tool_error
from src.services.booking.errors import BookingError


def _state(tool_calls, **overrides):
    values = {
        "query": "Tìm thông tin VF8",
        "messages": [AIMessage(content="", tool_calls=tool_calls)],
    }
    values.update(overrides)
    return values


def _call(name, args=None, call_id="call-1"):
    return {"name": name, "args": args or {}, "id": call_id, "type": "tool_call"}


def test_booking_error_is_serialized_for_agent_clarification():
    content = serialize_tool_error(
        BookingError("INVALID_INPUT", "Ngày kết thúc phải bằng hoặc sau ngày bắt đầu.")
    )

    assert '"code": "INVALID_INPUT"' in content
    assert "Ngày kết thúc phải bằng hoặc sau ngày bắt đầu." in content


@pytest.mark.asyncio
async def test_guarded_tool_node_returns_structured_booking_error():
    @tool("search_test_drive_options")
    def failing_search(preferred_date_from: str, preferred_date_to: str) -> dict:
        """Fake search that rejects a reversed date range."""
        raise BookingError("INVALID_INPUT", "Ngày kết thúc phải bằng hoặc sau ngày bắt đầu.")

    node = build_guarded_tool_node([failing_search], skill_name="booking")
    graph = StateGraph(AgentState)
    graph.add_node("tools", node)
    graph.set_entry_point("tools")
    graph.add_edge("tools", END)
    agent = graph.compile()
    result = await agent.ainvoke(
        _state(
            [
                _call(
                    "search_test_drive_options",
                    {
                        "preferred_date_from": "2026-08-26",
                        "preferred_date_to": "2026-08-21",
                    },
                )
            ]
        )
    )

    message = next(message for message in result["messages"] if isinstance(message, ToolMessage))
    assert isinstance(message, ToolMessage)
    assert message.status == "error"
    assert '"code": "INVALID_INPUT"' in message.content
    assert "Ngày kết thúc phải bằng hoặc sau ngày bắt đầu." in message.content


def test_allows_tool_inside_active_skill_allowlist():
    decision = inspect_tool_calls(
        _state([_call("search_knowledge", {"query": "VF8"})]),
        allowed_tool_names={"search_knowledge"},
        settings=Settings(),
    )

    assert decision.allowed is True


def test_blocks_tool_outside_active_skill_allowlist():
    decision = inspect_tool_calls(
        _state([_call("confirm_test_drive_booking", {"booking_id": "b1"})]),
        allowed_tool_names={"search_knowledge"},
        settings=Settings(),
    )

    assert decision.allowed is False
    assert decision.code == "TOOL_NOT_ALLOWED"


def test_blocks_duplicate_tool_calls_in_same_message():
    calls = [
        _call("search_knowledge", {"query": "VF8"}, "call-1"),
        _call("search_knowledge", {"query": "VF8"}, "call-2"),
    ]
    decision = inspect_tool_calls(
        _state(calls),
        allowed_tool_names={"search_knowledge"},
        settings=Settings(),
    )

    assert decision.allowed is False
    assert decision.code == "DUPLICATE_TOOL_CALL"


def test_blocks_booking_confirmation_without_explicit_user_confirmation():
    call = _call(
        "confirm_test_drive_booking",
        {"booking_id": "b1", "expected_version": 1, "ui_action_id": "ui-1"},
    )
    decision = inspect_tool_calls(
        _state([call], query="Cho tôi xem lại thông tin"),
        allowed_tool_names={"confirm_test_drive_booking"},
        settings=Settings(),
    )

    assert decision.allowed is False
    assert decision.code == "EXPLICIT_CONFIRMATION_REQUIRED"


@pytest.mark.parametrize(
    ("tool_name", "arguments"),
    [
        (
            "cancel_booking",
            {
                "booking_id": "b1",
                "access_session_token": "session",
                "ui_action_id": "cancel:one",
            },
        ),
        (
            "reschedule_booking",
            {
                "current_booking_id": "b1",
                "new_slot_id": "slot-2",
                "access_session_token": "session",
                "ui_action_id": "reschedule:one",
            },
        ),
    ],
)
def test_destructive_management_tools_require_bound_structured_confirmation(tool_name, arguments):
    blocked = inspect_tool_calls(
        _state([_call(tool_name, arguments)]),
        allowed_tool_names={tool_name},
        settings=Settings(),
    )
    allowed = inspect_tool_calls(
        _state(
            [_call(tool_name, arguments)],
            requested_action=tool_name,
            action_payload=arguments,
        ),
        allowed_tool_names={tool_name},
        settings=Settings(),
    )

    assert blocked.code == "EXPLICIT_CONFIRMATION_REQUIRED"
    assert allowed.allowed is True


@pytest.mark.parametrize(
    "query",
    [
        "Tôi xác nhận chốt lịch này",
        "Tôi đồng ý nhận tư vấn về VF8",
        "Can you explain what confirm means?",
    ],
)
def test_natural_language_alone_never_authorizes_booking_confirmation(query):
    call = _call(
        "confirm_test_drive_booking",
        {"booking_id": "b1", "expected_version": 1, "ui_action_id": "ui-1"},
    )
    decision = inspect_tool_calls(
        _state([call], query=query),
        allowed_tool_names={"confirm_test_drive_booking"},
        settings=Settings(),
    )

    assert decision.allowed is False
    assert decision.code == "EXPLICIT_CONFIRMATION_REQUIRED"


@pytest.mark.parametrize(
    "query",
    [
        "Tôi không xác nhận lịch này",
        "Chưa chốt lịch nhé",
        "Đừng đồng ý đặt lịch",
        "Do not confirm this booking",
        "I don't want to book now",
    ],
)
def test_blocks_confirmation_when_user_phrase_is_explicitly_negated(query):
    call = _call(
        "confirm_test_drive_booking",
        {"booking_id": "b1", "expected_version": 1, "ui_action_id": "ui-1"},
    )
    decision = inspect_tool_calls(
        _state([call], query=query),
        allowed_tool_names={"confirm_test_drive_booking"},
        settings=Settings(),
    )

    assert decision.allowed is False
    assert decision.code == "EXPLICIT_CONFIRMATION_REQUIRED"


def test_blocks_batch_containing_a_mutating_tool():
    calls = [
        _call("get_booking_draft", {"booking_id": "b1"}, "call-1"),
        _call("update_booking_draft", {"booking_id": "b1"}, "call-2"),
    ]
    decision = inspect_tool_calls(
        _state(calls),
        allowed_tool_names={"get_booking_draft", "update_booking_draft"},
        settings=Settings(),
    )

    assert decision.allowed is False
    assert decision.code == "MUTATION_BATCH_NOT_ALLOWED"


def test_blocks_invalid_tool_state_without_ai_tool_message():
    decision = inspect_tool_calls(
        {"messages": []},
        allowed_tool_names={"search_knowledge"},
        settings=Settings(),
    )

    assert decision.allowed is False
    assert decision.code == "INVALID_TOOL_STATE"


def test_blocks_more_tool_calls_than_configured_limit():
    calls = [
        _call("search_knowledge", {"query": "VF8"}, "call-1"),
        _call("get_booking_draft", {"booking_id": "b1"}, "call-2"),
    ]
    decision = inspect_tool_calls(
        _state(calls),
        allowed_tool_names={"search_knowledge", "get_booking_draft"},
        settings=Settings(guardrails_max_tool_calls_per_message=1),
    )

    assert decision.allowed is False
    assert decision.code == "TOOL_CALL_LIMIT_EXCEEDED"


def test_blocks_tool_arguments_that_are_not_an_object():
    message = AIMessage.model_construct(
        content="",
        tool_calls=[
            {
                "name": "search_knowledge",
                "args": "VF8",
                "id": "call-invalid-args",
                "type": "tool_call",
            }
        ],
    )
    decision = inspect_tool_calls(
        {"messages": [message]},
        allowed_tool_names={"search_knowledge"},
        settings=Settings(),
    )

    assert decision.allowed is False
    assert decision.code == "INVALID_TOOL_ARGUMENTS"


def test_blocks_tool_arguments_that_exceed_payload_limits():
    decision = inspect_tool_calls(
        _state([_call("search_knowledge", {"query": "x" * 5001})]),
        allowed_tool_names={"search_knowledge"},
        settings=Settings(),
    )

    assert decision.allowed is False
    assert decision.code == "TOOL_PAYLOAD_LIMIT_EXCEEDED"


def test_allows_multiple_distinct_read_only_tools_within_budget():
    calls = [
        _call("search_knowledge", {"query": "VF8"}, "call-1"),
        _call("get_booking_draft", {"booking_id": "b1"}, "call-2"),
    ]
    decision = inspect_tool_calls(
        _state(calls),
        allowed_tool_names={"search_knowledge", "get_booking_draft"},
        settings=Settings(),
    )

    assert decision.allowed is True


def test_allows_structured_confirmation_without_natural_language_confirmation():
    call = _call(
        "confirm_test_drive_booking",
        {"booking_id": "b1", "expected_version": 1, "ui_action_id": "ui-1"},
    )
    decision = inspect_tool_calls(
        _state(
            [call],
            query="Cho tôi xem lại",
            requested_action="confirm_booking",
            action_payload={"booking_id": "b1", "expected_version": 1, "ui_action_id": "ui-1"},
        ),
        allowed_tool_names={"confirm_test_drive_booking"},
        settings=Settings(),
    )

    assert decision.allowed is True


@pytest.mark.parametrize(
    ("requested_action", "action_payload"),
    [
        (
            "search_options",
            {"booking_id": "b1", "expected_version": 1, "ui_action_id": "ui-1"},
        ),
        (
            "confirm_booking",
            {"booking_id": "other", "expected_version": 1, "ui_action_id": "ui-1"},
        ),
        (
            "confirm_booking",
            {"booking_id": "b1", "expected_version": 2, "ui_action_id": "ui-1"},
        ),
        (
            "confirm_booking",
            {"booking_id": "b1", "expected_version": 1, "ui_action_id": "confirm:other"},
        ),
    ],
)
def test_blocks_confirmation_not_bound_to_exact_structured_payload(requested_action, action_payload):
    call = _call(
        "confirm_test_drive_booking",
        {"booking_id": "b1", "expected_version": 1, "ui_action_id": "ui-1"},
    )
    decision = inspect_tool_calls(
        _state(
            [call],
            requested_action=requested_action,
            action_payload=action_payload,
        ),
        allowed_tool_names={"confirm_test_drive_booking"},
        settings=Settings(),
    )

    assert decision.allowed is False
    assert decision.code == "EXPLICIT_CONFIRMATION_REQUIRED"


def test_blocks_two_mutating_tools_in_one_message():
    calls = [
        _call("hold_test_drive_slot", {"slot_id": "s1", "ui_action_id": "ui-1"}, "call-1"),
        _call("update_booking_draft", {"booking_id": "b1"}, "call-2"),
    ]
    decision = inspect_tool_calls(
        _state(calls),
        allowed_tool_names={"hold_test_drive_slot", "update_booking_draft"},
        settings=Settings(),
    )

    assert decision.allowed is False
    assert decision.code == "MUTATION_BATCH_NOT_ALLOWED"


@pytest.mark.asyncio
async def test_guarded_tool_node_does_not_execute_blocked_confirmation():
    executed = MagicMock()

    @tool("confirm_test_drive_booking")
    def fake_confirmation(booking_id: str) -> dict:
        """Fake high-impact tool used to verify that blocking prevents execution."""
        executed(booking_id)
        return {"booking_id": booking_id}

    node = build_guarded_tool_node([fake_confirmation], skill_name="booking")
    result = await node(
        _state(
            [_call("confirm_test_drive_booking", {"booking_id": "b1"})],
            query="Chỉ hiển thị thông tin",
        )
    )

    executed.assert_not_called()
    assert len(result["messages"]) == 1
    assert isinstance(result["messages"][0], ToolMessage)
    assert result["messages"][0].status == "error"
    assert "EXPLICIT_CONFIRMATION_REQUIRED" in result["messages"][0].content


@pytest.mark.asyncio
async def test_guarded_tool_node_executes_when_guardrails_are_disabled(monkeypatch):
    executed = MagicMock()

    @tool("confirm_test_drive_booking")
    def fake_confirmation(booking_id: str) -> dict:
        """Fake tool for the explicit guardrails-disabled configuration branch."""
        executed(booking_id)
        return {"booking_id": booking_id}

    monkeypatch.setattr(
        "src.guardrails.tool_guard.get_settings",
        lambda: Settings(guardrails_enabled=False),
    )
    node = build_guarded_tool_node([fake_confirmation], skill_name="booking")
    graph = StateGraph(AgentState)
    graph.add_node("tools", node)
    graph.set_entry_point("tools")
    graph.add_edge("tools", END)
    agent = graph.compile()
    result = await agent.ainvoke(
        _state(
            [_call("confirm_test_drive_booking", {"booking_id": "b1"})],
            query="Chỉ hiển thị thông tin",
        )
    )

    executed.assert_called_once_with("b1")
    tool_messages = [message for message in result["messages"] if isinstance(message, ToolMessage)]
    assert len(tool_messages) == 1
    assert tool_messages[0].status == "success"
