from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import HumanMessage
from src.agents.nodes import classifier_node as classifier_module
from src.agents.nodes.classifier_node import RouteSchema, classifier_node
from src.agents.nodes.sensitive_policy_node import sensitive_policy_node


# test case of Chau + kiểm tra classifier xử lý query rỗng mà không gọi LLM
@pytest.mark.asyncio
async def test_classifier_empty_query_uses_booking_route_without_llm(monkeypatch):
    get_llm = MagicMock(side_effect=AssertionError("LLM must not be called"))
    monkeypatch.setattr(classifier_module, "get_classifier_llm", get_llm)

    result = await classifier_node({"query": "", "metadata": {"trace_id": "trace-1"}})

    assert result["intent"] == "domain"
    assert result["active_skill"] == "booking"
    assert result["metadata"] == {"trace_id": "trace-1", "sub_intent": "empty_query"}
    assert isinstance(result["messages"][0], HumanMessage)
    assert result["messages"][0].content == ""
    get_llm.assert_not_called()


@pytest.mark.asyncio
async def test_classifier_prompt_marks_colloquial_locations_as_booking(monkeypatch):
    structured = MagicMock()
    structured.ainvoke = AsyncMock(
        return_value=RouteSchema(
            intent="domain", sub_intent="booking_new", has_schedule_preference=False
        )
    )
    llm = MagicMock()
    llm.model_name = "test-classifier"
    llm.with_structured_output.return_value = structured
    monkeypatch.setattr(classifier_module, "get_classifier_llm", lambda: llm)

    result = await classifier_node({"query": "t ở Hồ Chí Minh"})

    prompt = structured.ainvoke.await_args.args[0]
    assert "t ở hcm" in prompt
    assert result["intent"] == "domain"
    assert result["metadata"]["sub_intent"] == "booking_new"


@pytest.mark.asyncio
async def test_classifier_marks_schedule_questions_as_booking_availability(monkeypatch):
    structured = MagicMock()
    structured.ainvoke = AsyncMock(
        return_value=RouteSchema(
            intent="domain", sub_intent="booking_availability", has_schedule_preference=True
        )
    )
    llm = MagicMock()
    llm.model_name = "test-classifier"
    llm.with_structured_output.return_value = structured
    monkeypatch.setattr(classifier_module, "get_classifier_llm", lambda: llm)

    result = await classifier_node({"query": "tui rảnh ngày 25-26"})

    prompt = structured.ainvoke.await_args.args[0]
    assert "booking_availability" in prompt
    assert result["intent"] == "domain"
    assert result["metadata"]["sub_intent"] == "booking_availability"


@pytest.mark.asyncio
async def test_classifier_corrects_new_test_drive_discovery_misrouted_as_booking_lookup(monkeypatch):
    structured = MagicMock()
    structured.ainvoke = AsyncMock(
        return_value=RouteSchema(
            intent="domain",
            sub_intent="booking_lookup",
            has_schedule_preference=True,
        )
    )
    llm = MagicMock()
    llm.model_name = "test-classifier"
    llm.with_structured_output.return_value = structured
    monkeypatch.setattr(classifier_module, "get_classifier_llm", lambda: llm)

    result = await classifier_node({"query": "Xem lich chay thu VF7 o showroom Thanh Ha"})

    assert result["intent"] == "domain"
    assert result["active_skill"] == "booking"
    assert result["metadata"]["sub_intent"] == "booking_availability"


@pytest.mark.asyncio
async def test_classifier_treats_relationship_only_as_new_booking_not_contact(monkeypatch):
    structured = MagicMock()
    structured.ainvoke = AsyncMock(
        return_value=RouteSchema(
            intent="domain",
            sub_intent="booking_provide_contact",
            has_schedule_preference=False,
        )
    )
    llm = MagicMock()
    llm.model_name = "test-classifier"
    llm.with_structured_output.return_value = structured
    monkeypatch.setattr(classifier_module, "get_classifier_llm", lambda: llm)

    result = await classifier_node(
        {"query": "Tôi đặt lịch giúp em trai tôi lái thử VF 7"}
    )

    assert result["intent"] == "domain"
    assert result["active_skill"] == "booking"
    assert result["metadata"]["sub_intent"] == "booking_new"


@pytest.mark.asyncio
async def test_classifier_keeps_contact_route_when_contact_is_actually_supplied(monkeypatch):
    structured = MagicMock()
    structured.ainvoke = AsyncMock(
        return_value=RouteSchema(
            intent="domain",
            sub_intent="booking_provide_contact",
            contact_value="an@example.test",
            has_schedule_preference=False,
        )
    )
    llm = MagicMock()
    llm.model_name = "test-classifier"
    llm.with_structured_output.return_value = structured
    monkeypatch.setattr(classifier_module, "get_classifier_llm", lambda: llm)

    result = await classifier_node(
        {
            "query": (
                "Tôi đặt lịch để Nguyễn Văn An lái thử VF 7, "
                "email an@example.test"
            )
        }
    )

    assert result["metadata"]["sub_intent"] == "booking_provide_contact"


@pytest.mark.asyncio
async def test_classifier_keeps_existing_booking_lookup_with_identity(monkeypatch):
    structured = MagicMock()
    structured.ainvoke = AsyncMock(
        return_value=RouteSchema(
            intent="domain",
            sub_intent="booking_lookup",
            has_schedule_preference=False,
        )
    )
    llm = MagicMock()
    llm.model_name = "test-classifier"
    llm.with_structured_output.return_value = structured
    monkeypatch.setattr(classifier_module, "get_classifier_llm", lambda: llm)

    result = await classifier_node({"query": "Xem lich VF7 toi da dat bang a@example.test"})

    assert result["metadata"]["sub_intent"] == "booking_lookup"


@pytest.mark.asyncio
async def test_classifier_corrects_ebus_test_drive_from_out_of_scope(monkeypatch):
    structured = MagicMock()
    structured.ainvoke = AsyncMock(
        return_value=RouteSchema(
            intent="out_of_scope",
            sub_intent="out_of_scope",
            has_schedule_preference=False,
        )
    )
    llm = MagicMock()
    llm.model_name = "test-classifier"
    llm.with_structured_output.return_value = structured
    monkeypatch.setattr(classifier_module, "get_classifier_llm", lambda: llm)

    result = await classifier_node({"query": "Toi muon lai thu EBus"})

    assert result["intent"] == "domain"
    assert result["metadata"]["sub_intent"] == "booking_new"


@pytest.mark.asyncio
async def test_classifier_corrects_short_schedule_preference_while_choosing_slot(monkeypatch):
    structured = MagicMock()
    structured.ainvoke = AsyncMock(
        return_value=RouteSchema(
            intent="domain",
            sub_intent="booking_new",
            has_schedule_preference=True,
        )
    )
    llm = MagicMock()
    llm.model_name = "test-classifier"
    llm.with_structured_output.return_value = structured
    monkeypatch.setattr(classifier_module, "get_classifier_llm", lambda: llm)

    result = await classifier_node(
        {
            "query": "thôi 28 t mới rảnh",
            "context": {
                "channel": "booking",
                "stage": "choose_slot",
                "selectedVehicle": {"id": "vf9", "name": "VF 9"},
                "selectedShowroom": {"id": "206", "name": "VinFast Lợi Mận Yên Mỹ"},
            },
        }
    )

    prompt = structured.ainvoke.await_args.args[0]
    assert "thôi 28 t mới rảnh" in prompt
    assert result["active_skill"] == "booking"
    assert result["metadata"]["sub_intent"] == "booking_availability"


@pytest.mark.asyncio
async def test_classifier_corrects_reschedule_to_availability_during_unconfirmed_slot_selection(monkeypatch):
    structured = MagicMock()
    structured.ainvoke = AsyncMock(
        return_value=RouteSchema(
            intent="domain",
            sub_intent="booking_reschedule",
            has_schedule_preference=True,
        )
    )
    llm = MagicMock()
    llm.model_name = "test-classifier"
    llm.with_structured_output.return_value = structured
    monkeypatch.setattr(classifier_module, "get_classifier_llm", lambda: llm)

    result = await classifier_node(
        {
            "query": "đổi ngày 25 đi",
            "context": {
                "channel": "booking",
                "stage": "choose_slot",
                "selectedVehicle": {"id": "vf9", "name": "VF 9"},
                "selectedShowroom": {"id": "60313", "name": "VinFast Minh Đạo Phát Nghĩa Trụ"},
            },
            "post_booking_context": {"active": False},
        }
    )

    assert result["active_skill"] == "booking"
    assert result["metadata"]["sub_intent"] == "booking_availability"


@pytest.mark.asyncio
async def test_classifier_keeps_reschedule_for_confirmed_booking(monkeypatch):
    structured = MagicMock()
    structured.ainvoke = AsyncMock(
        return_value=RouteSchema(
            intent="domain",
            sub_intent="booking_reschedule",
            has_schedule_preference=True,
            reschedule_date_type="explicit",
            reschedule_target_date="2026-08-28",
            reschedule_target_time="13:30",
        )
    )
    llm = MagicMock()
    llm.model_name = "test-classifier"
    llm.with_structured_output.return_value = structured
    monkeypatch.setattr(classifier_module, "get_classifier_llm", lambda: llm)

    result = await classifier_node(
        {
            "query": "đổi ngày 25 đi",
            "context": {"channel": "booking", "stage": "choose_slot"},
            "post_booking_context": {"active": True},
        }
    )

    assert result["active_skill"] == "booking"
    assert result["metadata"]["sub_intent"] == "booking_reschedule"
    assert result["intent_entities"]["reschedule_target_date"] == "2026-08-28"
    assert result["intent_entities"]["reschedule_target_time"] == "13:30"
    assert result["intent_entities"]["reschedule_date_type"] == "explicit"
    assert result["intent_entities"]["reschedule_day_offset"] is None


@pytest.mark.asyncio
async def test_classifier_merges_pending_reschedule_in_code_not_in_llm(monkeypatch):
    structured = MagicMock()
    structured.ainvoke = AsyncMock(
        return_value=RouteSchema(
            intent="domain",
            sub_intent="booking_reschedule",
            has_schedule_preference=True,
            reschedule_target_time="15:30",
        )
    )
    llm = MagicMock()
    llm.model_name = "test-classifier"
    llm.with_structured_output.return_value = structured
    monkeypatch.setattr(classifier_module, "get_classifier_llm", lambda: llm)

    result = await classifier_node(
        {
            "query": "đổi thành 15h30",
            "context": {
                "pendingReschedule": {
                    "reschedule_date_type": "explicit",
                    "reschedule_target_date": "2026-08-28",
                    "reschedule_day_offset": None,
                    "reschedule_target_time": "13:30",
                }
            },
            "post_booking_context": {"active": True},
        }
    )

    assert result["intent_entities"] == {
        "contact_value": None,
        "reschedule_date_type": "explicit",
        "reschedule_target_date": "2026-08-28",
        "reschedule_day_offset": None,
        "reschedule_target_time": "15:30",
    }


# test case of Chau + kiểm tra classifier ưu tiên sensitive keyword và không phụ thuộc LLM
@pytest.mark.asyncio
async def test_classifier_sensitive_keyword_bypasses_llm(monkeypatch):
    get_llm = MagicMock(side_effect=AssertionError("LLM must not be called"))
    monkeypatch.setattr(classifier_module, "get_classifier_llm", get_llm)

    result = await classifier_node({"query": "Hoàng Sa và Trường Sa thuộc về ai?"})

    assert result["intent"] == "sensitive"
    assert result["metadata"]["sub_intent"] == "sovereignty"
    assert result["messages"][0].content == "Hoàng Sa và Trường Sa thuộc về ai?"
    get_llm.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("query", "expected_sub_intent"),
    [
        ("Đảng Cộng sản Việt Nam được thành lập khi nào?", "party_history"),
        ("Chủ tịch Hồ Chí Minh là ai?", "ho_chi_minh_history"),
        ("Bác Hồ sinh năm nào?", "ho_chi_minh_history"),
    ],
)
async def test_classifier_civic_history_keywords_bypass_llm(
    monkeypatch,
    query,
    expected_sub_intent,
):
    get_llm = MagicMock(side_effect=AssertionError("LLM must not be called"))
    monkeypatch.setattr(classifier_module, "get_classifier_llm", get_llm)

    result = await classifier_node({"query": query})

    assert result["intent"] == "sensitive"
    assert result["metadata"]["sub_intent"] == expected_sub_intent
    get_llm.assert_not_called()


@pytest.mark.asyncio
async def test_classifier_does_not_confuse_ho_chi_minh_city_with_the_person(monkeypatch):
    structured = MagicMock()
    structured.ainvoke = AsyncMock(
        return_value=RouteSchema(
            intent="domain",
            sub_intent="booking_new",
            has_schedule_preference=False,
        )
    )
    llm = MagicMock()
    llm.model_name = "test-classifier"
    llm.with_structured_output.return_value = structured
    monkeypatch.setattr(classifier_module, "get_classifier_llm", lambda: llm)

    result = await classifier_node({"query": "Tôi đang ở Hồ Chí Minh"})

    assert result["intent"] == "domain"
    assert result["metadata"]["sub_intent"] == "booking_new"
    structured.ainvoke.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query",
    [
        "Tôi ở đường Trường Sa, TP.HCM, tìm showroom gần nhất",
        "Tôi ở đường Hoàng Sa, Đà Nẵng và muốn lái thử VF 9",
        "Tôi là đảng viên và muốn đặt lịch lái thử VF 3",
    ],
)
async def test_classifier_civic_words_in_booking_context_use_domain_route(monkeypatch, query):
    structured = MagicMock()
    structured.ainvoke = AsyncMock(
        return_value=RouteSchema(
            intent="domain",
            sub_intent="booking_new",
            has_schedule_preference=False,
        )
    )
    llm = MagicMock()
    llm.model_name = "test-classifier"
    llm.with_structured_output.return_value = structured
    monkeypatch.setattr(classifier_module, "get_classifier_llm", lambda: llm)

    result = await classifier_node({"query": query})

    assert result["intent"] == "domain"
    assert result["metadata"]["sub_intent"] == "booking_new"
    structured.ainvoke.assert_awaited_once()


# test case of Chau + kiểm tra classifier map sub intent domain sang đúng active skill
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("sub_intent", "expected_skill"),
    [("booking", "booking"), ("vehicle_info", "booking")],
)
async def test_classifier_maps_domain_sub_intent_to_active_skill(monkeypatch, sub_intent, expected_skill):
    structured = MagicMock()
    structured.ainvoke = AsyncMock(
        return_value=RouteSchema(
            intent="domain", sub_intent=sub_intent, has_schedule_preference=False
        )
    )
    llm = MagicMock()
    llm.model_name = "test-classifier"
    llm.with_structured_output.return_value = structured
    monkeypatch.setattr(classifier_module, "get_classifier_llm", lambda: llm)

    result = await classifier_node({"query": "Yêu cầu thuộc domain", "metadata": {"request_id": "r-1"}})

    assert result["intent"] == "domain"
    assert result["active_skill"] == expected_skill
    assert result["metadata"]["request_id"] == "r-1"
    assert result["metadata"]["sub_intent"] == sub_intent
    assert result["metadata"]["llm_call_count"] == 1
    structured.ainvoke.assert_awaited_once()


@pytest.mark.asyncio
async def test_classifier_keeps_vehicle_info_inside_booking_channel(monkeypatch):
    structured = MagicMock()
    structured.ainvoke = AsyncMock(
        return_value=RouteSchema(
            intent="domain", sub_intent="vehicle_info", has_schedule_preference=False
        )
    )
    llm = MagicMock()
    llm.model_name = "test-classifier"
    llm.with_structured_output.return_value = structured
    monkeypatch.setattr(classifier_module, "get_classifier_llm", lambda: llm)

    result = await classifier_node(
        {
            "query": "Tôi muốn xem VF5",
            "context": {"channel": "booking", "stage": "need_car"},
        }
    )

    assert result["intent"] == "domain"
    assert result["active_skill"] == "booking"
    assert result["metadata"]["sub_intent"] == "vehicle_info"
    assert result["metadata"]["llm_call_count"] == 1


@pytest.mark.asyncio
async def test_classifier_keeps_new_test_drive_request_out_of_post_booking_shortcut(monkeypatch):
    structured = MagicMock()
    structured.ainvoke = AsyncMock(
        return_value=RouteSchema(
            intent="domain", sub_intent="booking_new", has_schedule_preference=False
        )
    )
    llm = MagicMock()
    llm.model_name = "test-classifier"
    llm.with_structured_output.return_value = structured
    monkeypatch.setattr(classifier_module, "get_classifier_llm", lambda: llm)

    result = await classifier_node({"query": "Tôi muốn lái thử VF9"})

    assert result["intent"] == "domain"
    assert result["active_skill"] == "booking"
    assert result["metadata"]["sub_intent"] == "booking_new"
    structured.ainvoke.assert_awaited_once()


@pytest.mark.asyncio
async def test_classifier_uses_llm_for_short_post_booking_reschedule(monkeypatch):
    structured = MagicMock()
    structured.ainvoke = AsyncMock(
        return_value=RouteSchema(
            intent="domain", sub_intent="booking_reschedule", has_schedule_preference=False
        )
    )
    llm = MagicMock()
    llm.model_name = "test-classifier"
    llm.with_structured_output.return_value = structured
    monkeypatch.setattr(classifier_module, "get_classifier_llm", lambda: llm)

    result = await classifier_node(
        {
            "query": "tôi muốn đổi giờ của lịch",
            "active_skill": "post_booking",
            "post_booking_context": {"active": True},
            "context": {"channel": "booking", "stage": "success"},
        }
    )

    assert result["intent"] == "domain"
    assert result["active_skill"] == "booking"
    assert result["metadata"]["sub_intent"] == "booking_reschedule"
    structured.ainvoke.assert_awaited_once()


@pytest.mark.asyncio
async def test_classifier_uses_llm_for_short_post_booking_advisory(monkeypatch):
    structured = MagicMock()
    structured.ainvoke = AsyncMock(
        return_value=RouteSchema(
            intent="domain", sub_intent="post_booking_advisory", has_schedule_preference=False
        )
    )
    llm = MagicMock()
    llm.model_name = "test-classifier"
    llm.with_structured_output.return_value = structured
    monkeypatch.setattr(classifier_module, "get_classifier_llm", lambda: llm)

    result = await classifier_node(
        {
            "query": "tôi cần mang gì",
            "active_skill": "post_booking",
            "post_booking_context": {"active": True},
        }
    )

    assert result["active_skill"] == "post_booking"
    assert result["metadata"]["sub_intent"] == "post_booking_advisory"
    structured.ainvoke.assert_awaited_once()


@pytest.mark.asyncio
async def test_driver_invitation_blocks_booking_availability(monkeypatch):
    structured = MagicMock()
    structured.ainvoke = AsyncMock(
        return_value=RouteSchema(
            intent="domain", sub_intent="booking_availability", has_schedule_preference=True
        )
    )
    llm = MagicMock()
    llm.model_name = "test-classifier"
    llm.with_structured_output.return_value = structured
    monkeypatch.setattr(classifier_module, "get_classifier_llm", lambda: llm)

    result = await classifier_node(
        {
            "query": "Ngày 25 còn giờ nào?",
            "participant_context": {"role": "driver"},
            "post_booking_context": {"active": True},
        }
    )

    assert result["intent"] == "out_of_scope"
    assert result["metadata"]["sub_intent"] == "driver_booking_scope"


@pytest.mark.asyncio
async def test_classifier_fallback_routes_without_network(monkeypatch):
    monkeypatch.setattr(
        classifier_module,
        "get_classifier_llm",
        MagicMock(side_effect=RuntimeError("classifier unavailable")),
    )

    result = await classifier_node({"query": "VF8 có gì nổi bật?"})

    assert result["intent"] == "domain"
    assert result.get("active_skill") == "booking"
    assert result["metadata"]["sub_intent"].startswith("fallback_")


@pytest.mark.asyncio
async def test_classifier_fallback_routes_reschedule_to_booking(monkeypatch):
    monkeypatch.setattr(
        classifier_module,
        "get_classifier_llm",
        MagicMock(side_effect=RuntimeError("classifier unavailable")),
    )

    result = await classifier_node(
        {
            "query": "tôi muốn đổi giờ của lịch",
            "active_skill": "post_booking",
            "post_booking_context": {"active": True},
        }
    )

    assert result["intent"] == "domain"
    assert result["active_skill"] == "booking"
    assert result["metadata"]["sub_intent"] == "booking_reschedule"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("query", "llm_sub_intent"),
    [
        ("hi", "greeting"),
        ("HI!!!", "greeting"),
        ("bạn là ai", "assistant_identity"),
        ("ViVi hỗ trợ gì?", "assistant_identity"),
    ],
)
async def test_classifier_uses_llm_for_greeting_and_identity(monkeypatch, query, llm_sub_intent):
    structured = MagicMock()
    structured.ainvoke = AsyncMock(
        return_value=RouteSchema(
            intent="domain", sub_intent=llm_sub_intent, has_schedule_preference=False
        )
    )
    llm = MagicMock()
    llm.model_name = "test-classifier"
    llm.with_structured_output.return_value = structured
    monkeypatch.setattr(classifier_module, "get_classifier_llm", lambda: llm)

    result = await classifier_node({"query": query})

    assert result["intent"] == "domain"
    assert result["active_skill"] == "booking"
    assert result["metadata"]["sub_intent"] == llm_sub_intent
    prompt = structured.ainvoke.await_args.args[0]
    assert "Never classify them as out_of_scope" in prompt
    assert "assistant_identity" in prompt


@pytest.mark.asyncio
async def test_classifier_uses_llm_for_booking_keyword(monkeypatch):
    structured = MagicMock()
    structured.ainvoke = AsyncMock(
        return_value=RouteSchema(
            intent="domain", sub_intent="booking_new", has_schedule_preference=False
        )
    )
    llm = MagicMock()
    llm.model_name = "test-classifier"
    llm.with_structured_output.return_value = structured
    monkeypatch.setattr(classifier_module, "get_classifier_llm", lambda: llm)

    result = await classifier_node({"query": "Tôi muốn đặt lịch lái thử VF6"})

    assert result["intent"] == "domain"
    assert result["active_skill"] == "booking"
    assert result["metadata"]["sub_intent"] == "booking_new"
    structured.ainvoke.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("exception", "internal_code"),
    [
        (classifier_module.BudgetExceededError("budget"), "LLM_BUDGET_EXCEEDED"),
        (classifier_module.LLMCallLimitExceededError("calls"), "LLM_CALL_LIMIT_EXCEEDED"),
    ],
)
async def test_classifier_returns_safe_response_when_llm_limit_is_exceeded(
    monkeypatch, exception, internal_code
):
    llm = MagicMock()
    llm.model_name = "test-classifier"
    llm.with_structured_output.return_value = MagicMock()
    monkeypatch.setattr(classifier_module, "get_classifier_llm", lambda: llm)
    trace = MagicMock()
    monkeypatch.setattr(classifier_module, "trace_event", trace)
    monkeypatch.setattr(
        classifier_module,
        "invoke_with_budget",
        AsyncMock(side_effect=exception),
    )

    result = await classifier_node({"query": "hi"})

    assert result["intent"] == "sensitive"
    assert result["action_error"] == "SERVICE_TEMPORARILY_UNAVAILABLE"
    assert result["policy_response"] == result["response"]
    assert "AI" not in result["response"]
    assert "chi phí" not in result["response"]
    assert any(call.kwargs.get("error_code") == internal_code for call in trace.call_args_list)


@pytest.mark.asyncio
async def test_classifier_falls_back_when_llm_is_not_configured(monkeypatch):
    monkeypatch.setattr(classifier_module, "get_classifier_llm", lambda: None)

    result = await classifier_node({"query": "VF8 có gì nổi bật?"})

    assert result["intent"] == "domain"
    assert result["active_skill"] == "booking"
    assert result["metadata"]["sub_intent"] == "fallback_domain"


# test case of Chau + kiểm tra classifier từ chối intent lạ do LLM trả về
@pytest.mark.asyncio
async def test_classifier_rejects_unknown_llm_intent(monkeypatch):
    structured = MagicMock()
    structured.ainvoke = AsyncMock(
        return_value=RouteSchema(
            intent="unknown", sub_intent="booking", has_schedule_preference=False
        )
    )
    llm = MagicMock()
    llm.with_structured_output.return_value = structured
    monkeypatch.setattr(classifier_module, "get_classifier_llm", lambda: llm)

    result = await classifier_node({"query": "Đặt lịch VF6"})

    assert result["intent"] in {"domain", "sensitive"}


# test case of Chau + kiểm tra sensitive node trả đúng policy cho từng sub intent
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("sub_intent", "expected_text"),
    [
        ("sovereignty", "Việt Nam"),
        ("party_history", "3/2/1930"),
        ("ho_chi_minh_history", "1890–1969"),
        ("out_of_scope_code", "không hỗ trợ viết mã"),
        ("out_of_scope_math", "giải các bài toán"),
        ("out_of_scope", "tìm showroom"),
        ("post_booking_required", "đã có lịch lái thử"),
        ("unknown", "Việt Nam"),
    ],
)
async def test_sensitive_policy_covers_all_sub_intent_branches(sub_intent, expected_text):
    result = await sensitive_policy_node({"metadata": {"sub_intent": sub_intent}})

    assert expected_text in result["response"]
    assert result["policy_response"] == result["response"]
