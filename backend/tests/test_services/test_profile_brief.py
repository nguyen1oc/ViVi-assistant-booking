import json

import pytest
import src.services.llm as llm_service
from langchain_core.messages import AIMessage
from src.services.profile.models import BookingSignalCandidate, SignalCandidate
from src.services.profile.queue import ProfileUpdateQueue
from src.services.profile.service import ProfileService


def _booking_signal(key, value, description, *, subject="group", operation="add"):
    return BookingSignalCandidate(
        category="fact",
        key=key,
        value=value,
        description=description,
        subject=subject,
        certainty="known",
        confidence=1,
        source_type="explicit_user",
        operation=operation,
    )


def _profile_service_with_booking(booking_db, confirmed_booking_factory):
    booking = confirmed_booking_factory()
    service = ProfileService(booking_db, identity_secret="test-secret")
    profile = service.promote_from_booking(
        None,
        booking["booking_id"],
        source="test",
    )
    assert profile is not None
    return service, booking["booking_id"], profile.id


def test_sales_brief_source_keeps_profile_and_booking_facts_separate(
    booking_db,
    confirmed_booking_factory,
):
    service, booking_id, profile_id = _profile_service_with_booking(
        booking_db,
        confirmed_booking_factory,
    )
    service.apply(
        profile_id,
        [
            SignalCandidate(
                category="fact",
                key="household_size",
                value=6,
                description="Gia đình có 6 người.",
                certainty="known",
                confidence=1,
                source_type="explicit_user",
            ),
            SignalCandidate(
                category="usage",
                key="primary_use",
                value=["Đi lại nội thành và đưa đón con."],
                description="Sử dụng xe chủ yếu để đi nội thành và đưa đón con.",
                certainty="known",
                confidence=1,
                source_type="explicit_user",
            ),
        ],
        source_ref="conversation-test",
    )
    service.apply_booking_signals(
        booking_id,
        [
            _booking_signal("booker_attending", True, "Người đặt sẽ tham gia.", subject="booker"),
            _booking_signal("additional_guest_count", 5, "Có 5 người đi cùng."),
            _booking_signal(
                "additional_guest_context",
                ["Bé gái 2 tuổi đi cùng", "Chồng cũng muốn lái thử"],
                "Thông tin người đi cùng.",
            ),
            _booking_signal("booker_will_drive", True, "Người đặt sẽ lái.", subject="booker"),
        ],
        source_participant="booker",
        source_ref="conversation-test",
    )

    source = service.booking_profiles_context(booking_id)
    source["test_drive_context"] = service.booking_context_signals(booking_id)

    profile_signals = source["booker"]["profile"]["sections"]["known_facts"]
    assert any(item["key"] == "household_size" and item["value"] == 6 for item in profile_signals)
    booking_values = {
        (item["key"], item["subject"]): item["value"]
        for item in source["test_drive_context"]
    }
    assert booking_values[("additional_guest_count", "group")] == 5
    assert booking_values[("additional_guest_context", "group")] == [
        "Bé gái 2 tuổi đi cùng",
        "Chồng cũng muốn lái thử",
    ]
    assert not any(item["key"] == "additional_guest_count" for item in profile_signals)


@pytest.mark.asyncio
async def test_summarize_user_profile_uses_current_llm_contract(monkeypatch):
    calls: list[list[object]] = []

    class FakeLlm:
        async def ainvoke(self, messages):
            calls.append(messages)
            return AIMessage(content="## Khách hàng: Châu\n\n- Gia đình có 4 người.")

    monkeypatch.setattr(llm_service, "get_llm", lambda: FakeLlm())
    source = {
        "booking": {"vehicle_model": "VinFast VF 9"},
        "same_person": True,
        "booker": {
            "name": "Châu",
            "profile": {
                "sections": {
                    "facts": [
                        {
                            "key": "household_size",
                            "value": 4,
                            "description": "Gia đình có 4 người.",
                        }
                    ]
                }
            },
        },
        "test_drive_context": [],
    }

    brief = await llm_service.summarize_user_profile(source)

    assert brief == "## Khách hàng: Châu\n\n- Gia đình có 4 người."
    assert len(calls) == 1
    assert calls[0][0].content == llm_service.SALES_BRIEF_PROMPT_V2
    assert json.loads(calls[0][1].content) == source


@pytest.mark.asyncio
async def test_post_booking_queue_falls_back_to_sql_when_redis_is_unavailable(
    booking_db,
    confirmed_booking_factory,
):
    service, booking_id, profile_id = _profile_service_with_booking(
        booking_db,
        confirmed_booking_factory,
    )

    class UnavailableRedis:
        available = False

    queue = ProfileUpdateQueue(UnavailableRedis(), service)  # type: ignore[arg-type]
    saved = await queue.enqueue_post_booking(
        profile_updates=[
            {
                "profile_id": profile_id,
                "candidates": [
                    SignalCandidate(
                        category="fact",
                        key="household_size",
                        value=6,
                        description="Gia đình có 6 người.",
                        certainty="known",
                        confidence=1,
                        source_type="explicit_user",
                    ).model_dump(mode="json")
                ],
            }
        ],
        booking_id=booking_id,
        booking_candidates=[
            _booking_signal(
                "additional_guest_context",
                ["Bé gái 2 tuổi đi cùng"],
                "Bé gái đi cùng.",
            )
        ],
        speaker_role="booker",
        conversation_id="conversation-test",
        trace_id="trace-test",
    )

    assert saved is True
    assert service.load(profile_id).signals[0]["key"] == "household_size"
    assert service.booking_context_signals(booking_id)[0]["value"] == ["Bé gái 2 tuổi đi cùng"]


@pytest.mark.asyncio
async def test_exact_regression_facts_persist_through_the_current_public_queue(
    booking_db,
    confirmed_booking_factory,
):
    service, booking_id, profile_id = _profile_service_with_booking(
        booking_db,
        confirmed_booking_factory,
    )

    class UnavailableRedis:
        available = False

    queue = ProfileUpdateQueue(UnavailableRedis(), service)  # type: ignore[arg-type]
    saved = await queue.enqueue_post_booking(
        profile_updates=[
            {
                "profile_id": profile_id,
                "candidates": [
                    SignalCandidate(
                        category="fact",
                        key="household_size",
                        value=6,
                        description="Gia đình có 6 người.",
                        certainty="known",
                        confidence=1,
                        source_type="explicit_user",
                    ).model_dump(mode="json"),
                    SignalCandidate(
                        category="usage",
                        key="primary_use",
                        value=["di chuyển nội thành như đưa đón con đi trẻ"],
                        description="Mục đích sử dụng xe chính.",
                        certainty="known",
                        confidence=1,
                        source_type="explicit_user",
                    ).model_dump(mode="json"),
                ],
            }
        ],
        booking_id=booking_id,
        booking_candidates=[
            _booking_signal("booker_attending", True, "Người đặt đi cùng.", subject="booker"),
            _booking_signal("additional_guest_count", 5, "Có thêm 5 người đi cùng."),
            _booking_signal(
                "additional_guest_context",
                ["Bé gái 2 tuổi đi cùng", "Chồng đi cùng và cũng muốn lái thử"],
                "Thông tin người đi cùng.",
            ),
            _booking_signal("booker_will_drive", True, "Người đặt sẽ lái.", subject="booker"),
        ],
        speaker_role="booker",
        conversation_id="conversation-regression",
        trace_id="trace-regression",
    )

    assert saved is True
    source = service.booking_profiles_context(booking_id)
    source["test_drive_context"] = service.booking_context_signals(booking_id)
    encoded = json.dumps(source, ensure_ascii=False)
    assert all(
        term in encoded
        for term in (
            "Gia đình có 6 người",
            "Bé gái 2 tuổi đi cùng",
            "Chồng đi cùng và cũng muốn lái thử",
            "di chuyển nội thành như đưa đón con đi trẻ",
        )
    )
