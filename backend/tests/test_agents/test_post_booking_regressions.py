import importlib

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import ValidationError
from src.agents.nodes.post_booking_skill_node import (
    _extract_follow_ups,
    _repair_signal_tool_call,
    _replace_signal_tool_call,
    _signal_call_has_payload,
    _signal_tool_call,
)
from src.agents.tools.update_post_booking_signals.tool import queue_post_booking_signals
from src.services.knowledge.service import KnowledgeService
from src.services.profile.models import BookingSignalCandidate, ProfileSignalCandidate

signal_tool_module = importlib.import_module(
    "src.agents.tools.update_post_booking_signals.tool"
)
post_booking_module = importlib.import_module("src.agents.nodes.post_booking_skill_node")


def _booking_signal(
    key: str,
    value: object,
    *,
    subject: str,
    operation: str = "add",
) -> BookingSignalCandidate:
    return BookingSignalCandidate(
        category="fact",
        key=key,
        value=value,
        description=f"Booking fact: {key}",
        subject=subject,
        operation=operation,
    )


def test_follow_up_transport_keeps_up_to_two_unique_declarative_items():
    visible, follow_ups = _extract_follow_ups(
        'Nội dung trả lời. <<<FOLLOW_UPS>>>["Chuẩn bị trước buổi lái thử", '
        '"Tìm hiểu các tính năng an toàn"]<<<END_FOLLOW_UPS>>>'
    )

    assert visible == "Nội dung trả lời."
    assert follow_ups == [
        {"text": "Chuẩn bị trước buổi lái thử"},
        {"text": "Tìm hiểu các tính năng an toàn"},
    ]

    _, incomplete = _extract_follow_ups(
        'Trả lời. <<<FOLLOW_UPS>>>["Chỉ còn một mục hợp lệ", "Có dấu hỏi?"]<<<END_FOLLOW_UPS>>>'
    )
    assert incomplete == [{"text": "Chỉ còn một mục hợp lệ"}]


def test_inline_signal_repair_replaces_only_the_empty_signal_call():
    original = AIMessage(
        content="",
        tool_calls=[
            {
                "id": "knowledge-1",
                "name": "search_knowledge",
                "args": {"query": "VF 9"},
                "type": "tool_call",
            },
            {
                "id": "signal-empty",
                "name": "update_post_booking_signals",
                "args": {"profile_signals": [], "booking_signals": []},
                "type": "tool_call",
            },
        ],
    )
    repaired = {
        "id": "signal-repaired",
        "name": "update_post_booking_signals",
        "args": {
            "profile_signals": [],
            "booking_signals": [
                {
                    "category": "fact",
                    "key": "additional_guest_count",
                    "value": 4,
                    "subject": "group",
                }
            ],
        },
        "type": "tool_call",
    }

    result = _replace_signal_tool_call(original, repaired)

    assert [call["name"] for call in result.tool_calls] == [
        "search_knowledge",
        "update_post_booking_signals",
    ]
    assert _signal_call_has_payload(_signal_tool_call(result)) is True


@pytest.mark.asyncio
async def test_inline_signal_repair_forces_one_structured_tool_call(monkeypatch):
    repaired_message = AIMessage(
        content="",
        tool_calls=[
            {
                "id": "signal-repaired",
                "name": "update_post_booking_signals",
                "args": {
                    "profile_signals": [],
                    "booking_signals": [
                        {
                            "category": "fact",
                            "key": "additional_guest_count",
                            "value": 4,
                            "subject": "group",
                        }
                    ],
                },
                "type": "tool_call",
            }
        ],
    )

    class BoundRepairLlm:
        async def ainvoke(self, messages, config=None):
            assert isinstance(messages[-1], HumanMessage)
            assert config is None
            return repaired_message

    class RepairLlm:
        def bind_tools(self, tools, tool_choice):
            assert tools[0].name == "update_post_booking_signals"
            assert tool_choice == "update_post_booking_signals"
            return BoundRepairLlm()

    monkeypatch.setattr(
        post_booking_module,
        "get_classifier_llm",
        lambda: RepairLlm(),
    )

    call = await _repair_signal_tool_call(
        prompt="profile and booking context",
        messages=[HumanMessage(content="Gia đình có 5 người đến lái thử.")],
        trace_id="trace-1",
        config=None,
    )

    assert _signal_call_has_payload(call) is True


def test_knowledge_search_prioritizes_requested_topic_with_exact_model_scope():
    result = KnowledgeService().search(
        "VF 8 được bảo hành pin như thế nào và tôi nên kiểm tra gì trong buổi lái thử?",
        model_code="VF 8",
        topics=["warranty", "battery", "test_drive"],
    )

    assert any(fact["id"] == "vinfast.vf_8.faq.12" for fact in result["facts"])


def test_household_size_uses_the_registered_profile_contract():
    signal = ProfileSignalCandidate(
        category="fact",
        key="household_size",
        value=4,
        description="Gia đình có 4 người.",
        subject="self",
    )

    assert (signal.key, signal.value, signal.subject) == ("household_size", 4, "self")


def test_primary_use_alias_and_single_value_follow_the_current_schema():
    signal = ProfileSignalCandidate(
        category="usage",
        key="city_commute",
        value="đưa đón con trong nội thành",
        description="Chủ yếu dùng xe để đưa đón con.",
        subject="self",
    )

    assert signal.key == "primary_use"
    assert signal.value == ["đưa đón con trong nội thành"]


def test_booking_involvement_requires_the_current_enum_instead_of_boolean_coercion():
    with pytest.raises(ValidationError, match="none, low, medium, or high"):
        _booking_signal(
            "booker_evaluation_involvement",
            True,
            subject="booker",
        )

    signal = _booking_signal(
        "booker_evaluation_involvement",
        "high",
        subject="booker",
    )
    assert signal.value == "high"


@pytest.mark.asyncio
async def test_signal_queue_applies_server_provenance_and_public_scope_contract(monkeypatch):
    captured: dict[str, object] = {}

    class Queue:
        async def enqueue_post_booking(self, **kwargs):
            captured.update(kwargs)
            return True

    monkeypatch.setattr(signal_tool_module, "profile_update_queue", Queue())

    result = await queue_post_booking_signals(
        profile_signals=[
            ProfileSignalCandidate(
                category="fact",
                key="household_size",
                value=4,
                description="Gia đình có 4 người.",
                subject="self",
                certainty="possible",
                confidence=0.2,
                source_type="implicit_user",
            ),
            ProfileSignalCandidate(
                category="interest",
                key="feature_interest",
                value=["parking_cameras_and_sensors"],
                description="Người dùng hỏi về camera và cảm biến.",
                subject="self",
                certainty="known",
                confidence=1,
                source_type="explicit_user",
            ),
        ],
        booking_signals=[
            _booking_signal("additional_guest_count", 3, subject="group")
        ],
        profile_id="profile-1",
        metadata={"conversation_id": "conversation-1", "trace_id": "trace-1"},
        participant_context={"role": "booker", "booking_id": "booking-1"},
    )

    assert result == {
        "status": "queued",
        "profile_signal_count": 2,
        "booking_signal_count": 1,
    }
    profile_candidates = captured["profile_updates"][0]["candidates"]
    assert profile_candidates[0]["source_type"] == "explicit_user"
    assert profile_candidates[0]["certainty"] == "known"
    assert profile_candidates[0]["confidence"] == 0.9
    assert profile_candidates[1]["source_type"] == "implicit_user"
    assert profile_candidates[1]["certainty"] == "possible"
    assert profile_candidates[1]["confidence"] == 0.6
    assert captured["booking_id"] == "booking-1"
    assert captured["booking_candidates"][0].key == "additional_guest_count"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("message", "expected_profile_updates"),
    [
        ("Hôm đó gia đình tôi có 5 người đến lái thử.", 0),
        (
            "Gia đình tôi có 6 người nhưng hôm đó chỉ chồng và em bé đi cùng tôi.",
            1,
        ),
    ],
)
async def test_signal_queue_separates_household_size_from_appointment_headcount(
    monkeypatch,
    message,
    expected_profile_updates,
):
    captured: dict[str, object] = {}

    class Queue:
        async def enqueue_post_booking(self, **kwargs):
            captured.update(kwargs)
            return True

    monkeypatch.setattr(signal_tool_module, "profile_update_queue", Queue())
    result = await queue_post_booking_signals(
        profile_signals=[
            ProfileSignalCandidate(
                category="fact",
                key="household_size",
                value=5 if expected_profile_updates == 0 else 6,
                description=message,
                subject="self",
            )
        ],
        booking_signals=[
            _booking_signal("booker_attending", True, subject="booker"),
            _booking_signal("additional_guest_count", 4, subject="group"),
        ],
        profile_id="profile-1",
        metadata={"conversation_id": "conversation-1", "trace_id": "trace-1"},
        participant_context={"role": "booker", "booking_id": "booking-1"},
        current_user_message=message,
    )

    assert result["profile_signal_count"] == expected_profile_updates
    assert len(captured["profile_updates"]) == expected_profile_updates


@pytest.mark.asyncio
async def test_booking_signals_are_rejected_when_booking_context_is_unresolved(monkeypatch):
    class Queue:
        async def enqueue_post_booking(self, **_kwargs):
            raise AssertionError("queue must not be called without resolved booking context")

    monkeypatch.setattr(signal_tool_module, "profile_update_queue", Queue())

    result = await queue_post_booking_signals(
        profile_signals=[],
        booking_signals=[
            _booking_signal("additional_guest_count", 1, subject="group")
        ],
        profile_id="profile-1",
        metadata={"conversation_id": "conversation-1", "trace_id": "trace-1"},
        participant_context={"role": "booker"},
    )

    assert result == {"status": "skipped", "reason": "booking_context_not_resolved"}
