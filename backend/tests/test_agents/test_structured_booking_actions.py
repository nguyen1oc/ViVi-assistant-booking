import json

import pytest
from langchain_core.messages import HumanMessage, ToolMessage
from src.agents.graph import agent
from src.agents.nodes.booking_skill_node import booking_skill_node
from src.agents.nodes.classifier_node import classifier_node


@pytest.mark.asyncio
async def test_booking_context_routes_to_booking_without_llm():
    result = await classifier_node(
        {
            "query": "Tôi muốn tiếp tục",
            "context": {"channel": "booking", "stage": "choose_showroom"},
        }
    )

    assert result["intent"] == "domain"
    assert result["active_skill"] == "booking"
    assert result["metadata"]["sub_intent"] == "booking"


@pytest.mark.asyncio
async def test_structured_action_creates_the_expected_tool_call():
    result = await booking_skill_node(
        {
            "messages": [HumanMessage(content="Tôi chọn slot này")],
            "requested_action": "hold_slot",
            "action_payload": {"slot_id": "slot-1", "ui_action_id": "hold-1"},
        }
    )

    tool_call = result["messages"][0].tool_calls[0]
    assert tool_call["name"] == "hold_test_drive_slot"
    assert tool_call["args"] == {"slot_id": "slot-1", "ui_action_id": "hold-1"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("action", "payload", "expected_tool"),
    [
        (
            "cancel_booking",
            {
                "booking_id": "booking-1",
                "access_session_token": "session-1",
                "ui_action_id": "cancel:one",
            },
            "cancel_booking",
        ),
        (
            "reschedule_booking",
            {
                "current_booking_id": "booking-1",
                "new_slot_id": "slot-2",
                "access_session_token": "session-1",
                "ui_action_id": "reschedule:one",
            },
            "reschedule_booking",
        ),
    ],
)
async def test_destructive_management_actions_dispatch_only_as_structured_tools(
    action,
    payload,
    expected_tool,
):
    result = await booking_skill_node(
        {
            "messages": [HumanMessage(content="Tôi xác nhận thao tác")],
            "requested_action": action,
            "action_payload": payload,
        }
    )

    tool_call = result["messages"][0].tool_calls[0]
    assert tool_call["name"] == expected_tool
    assert tool_call["args"] == payload


@pytest.mark.asyncio
async def test_structured_action_exposes_tool_result_to_chat_contract():
    tool_result = {"booking_id": "bkg-1", "status": "held", "version": 1}
    result = await booking_skill_node(
        {
            "messages": [
                HumanMessage(content="Tôi chọn slot này"),
                ToolMessage(
                    content=json.dumps(tool_result),
                    tool_call_id="call-1",
                    name="hold_test_drive_slot",
                ),
            ],
            "requested_action": "hold_slot",
            "action_payload": {"slot_id": "slot-1", "ui_action_id": "hold-1"},
        }
    )

    assert result["action_tool"] == "hold_test_drive_slot"
    assert result["action_input"] == {"slot_id": "slot-1", "ui_action_id": "hold-1"}
    assert result["action_result"] == tool_result
    assert result["action_error"] == ""


@pytest.mark.asyncio
async def test_structured_action_runs_through_the_compiled_graph_and_tool_node():
    result = await agent.ainvoke(
        {
            "query": "Tôi xác nhận slot này",
            "context": {"channel": "booking", "stage": "choose_slot"},
            "requested_action": "hold_slot",
            "action_payload": {"slot_id": "missing-slot", "ui_action_id": "hold-missing-slot"},
            "action_result": None,
            "action_tool": "",
            "action_input": {},
            "action_error": "",
        },
        config={"configurable": {"thread_id": "structured-action-tool-node"}},
    )

    assert result["action_tool"] == "hold_test_drive_slot"
    assert result["action_result"] is None
    assert result["action_error"]


@pytest.mark.asyncio
async def test_structured_action_strips_toolnode_exception_wrapper_from_user_error():
    result = await booking_skill_node(
        {
            "messages": [
                HumanMessage(content="Tôi xác nhận slot này"),
                ToolMessage(
                    content="Error: BookingError('Slot đã bắt đầu hoặc đã qua.')\n Please fix your mistakes.",
                    tool_call_id="call-1",
                    name="hold_test_drive_slot",
                    status="error",
                ),
            ],
            "requested_action": "hold_slot",
            "action_payload": {"slot_id": "slot-1", "ui_action_id": "hold-1"},
        }
    )

    expected_message = "Khung giờ này đã qua hoặc không còn khả dụng, vui lòng chọn giờ khác."
    assert result["response"] == expected_message
    assert result["action_error"] == "SLOT_NO_LONGER_AVAILABLE"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("code", "message_fragment"),
    [
        ("VEHICLE_NOT_FOUND", "mẫu xe"),
        ("OTP_INVALID", "OTP không đúng"),
        ("OTP_EXPIRED", "OTP đã hết hạn"),
    ],
)
async def test_structured_action_preserves_public_domain_error_codes(code, message_fragment):
    result = await booking_skill_node(
        {
            "messages": [
                HumanMessage(content="Thực hiện thao tác"),
                ToolMessage(
                    content=json.dumps({"error": {"code": code, "message": "internal"}}),
                    tool_call_id="call-error",
                    name="verify_booking_access",
                    status="error",
                ),
            ],
            "requested_action": "verify_access",
            "action_payload": {"challenge_id": "otp-1", "otp_code": "000000"},
        }
    )

    assert result["action_error"] == code
    assert message_fragment in result["response"]


@pytest.mark.asyncio
async def test_structured_confirmation_response_contains_booking_code():
    result = await booking_skill_node(
        {
            "messages": [
                HumanMessage(content="Xác nhận lịch"),
                ToolMessage(
                    content=json.dumps({"booking_id": "bkg-1", "booking_code": "VF260824ABC123"}),
                    tool_call_id="call-confirm",
                    name="confirm_test_drive_booking",
                ),
            ],
            "requested_action": "confirm_booking",
            "action_payload": {
                "booking_id": "bkg-1",
                "expected_version": 2,
                "ui_action_id": "confirm:test",
            },
        }
    )

    assert result["action_error"] == ""
    assert "VF260824ABC123" in result["response"]
