from __future__ import annotations

import argparse
import csv
import json
import os
import sqlite3
import subprocess
from contextlib import closing
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from src.database import Database
from src.evaluation.agent_benchmark import (
    DEFAULT_GOLDEN_PATH,
    DEFAULT_NEGATIVE_PATH,
    _argument_scores,
    _arguments_with_tool_evidence,
    _backup_sqlite_database,
    _brief_term_present,
    _classifier_route_score,
    _deterministic_behavior_checks,
    _estimate_model_costs,
    _eval_fixture_email,
    _evaluate_database_assertions,
    _evaluate_slot_availability,
    _generate_eval_sales_profile,
    _parse_model_price,
    _prepare_eval_case,
    _profile_scope_violation_check,
    _redact,
    _resolve_eval_turn_content,
    _resolve_eval_value,
    _slot_selection_score,
    _trusted_grounding_context,
    _UsageCollector,
    judge_recorded_predictions,
    load_golden_dataset,
    merge_prediction_payloads,
    render_markdown,
    run_live_predictions,
    run_negative_fixture_predictions,
    score_evaluation,
)
from src.evaluation.stability import aggregate_stability
from src.services.booking.common import is_valid_customer_email


@pytest.mark.parametrize(
    "brief",
    [
        "Có 4 thành viên gia đình đi cùng.",
        "Có 4 khách gia đình sẽ tham dự cùng.",
        "Có thêm 4 khách thuộc gia đình tham dự.",
        "Có thêm 4 khách thuộc gia đình; dự kiến tổng cộng 5 người tham dự.",
    ],
)
def test_brief_required_term_accepts_local_attendance_paraphrases(brief):
    assert _brief_term_present("4 người đi cùng", brief)


def test_brief_required_term_rejects_negated_attendance():
    assert not _brief_term_present(
        "4 người đi cùng",
        "Có 4 khách thuộc gia đình nhưng chưa tham dự.",
    )


def test_profile_scope_check_uses_registered_signal_taxonomy():
    valid_profile_call = {
        "name": "update_post_booking_signals",
        "status": "success",
        "arguments": {
            "profile_signals": [
                {"key": "household_size", "value": 4, "subject": "self"}
            ],
            "booking_signals": [],
        },
    }
    misplaced_booking_call = deepcopy(valid_profile_call)
    misplaced_booking_call["arguments"]["profile_signals"][0] = {
        "key": "booker_attending",
        "value": True,
        "subject": "booker",
    }
    booking_only_call = deepcopy(valid_profile_call)
    booking_only_call["arguments"] = {
        "profile_signals": [],
        "booking_signals": [
            {"key": "booker_attending", "value": True, "subject": "booker"}
        ],
    }

    assert _profile_scope_violation_check([valid_profile_call]) is False
    assert _profile_scope_violation_check([misplaced_booking_call]) is True
    assert _profile_scope_violation_check([booking_only_call]) is False
    assert _deterministic_behavior_checks(
        ["store_booking_context_as_profile"],
        response="Đã ghi nhận.",
        calls=[valid_profile_call],
        action_error="",
    ) == {"store_booking_context_as_profile": False}


def test_golden_datetime_contract_auto_holds_an_exact_requested_slot():
    dataset = load_golden_dataset(DEFAULT_GOLDEN_PATH)
    case = next(
        item for item in dataset["cases"]
        if item["case_id"] == "HARD-SEARCH-DATETIME-001"
    )

    assert case["expected"]["intent"] == "hold_slot"
    assert case["expected"]["tool"] == "search_test_drive_options"
    assert case["expected"]["database_assertions"] == [
        {"table": "bookings", "status": "held"},
        {"table": "test_drive_slots", "status": "held"},
    ]


def test_golden_loader_rejects_stale_post_booking_signal_category(tmp_path):
    dataset_path = tmp_path / "golden.json"
    dataset_path.write_text(
        json.dumps(
            {
                "case_count": 1,
                "cases": [
                    {
                        "case_id": "STALE-SIGNAL-001",
                        "evaluation_setup": {
                            "booking_signals": [
                                {
                                    "category": "attendance",
                                    "key": "booker_attending",
                                    "value": True,
                                    "subject": "booker",
                                }
                            ]
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match=r"STALE-SIGNAL-001 evaluation_setup\.booking_signals\[0\]",
    ):
        load_golden_dataset(dataset_path)


def test_classifier_intent_is_scored_independently_from_tool_selection():
    case = {"expected": {"intent": "search_options"}}
    prediction = {
        "turns": [
            {
                "role": "user",
                "classifier_intent": "domain",
                "classifier_sub_intent": "booking_availability",
            }
        ],
        "tool_calls": [{"name": "wrong_tool"}],
    }

    assert _classifier_route_score(case, prediction)["passed"] is True


def test_classifier_multi_turn_contract_scores_lookup_turn_not_otp_continuation():
    case = {
        "expected": {
            "intent": "get_booking_details",
            "classifier_turn_expectations": [
                {
                    "turn": 1,
                    "outer_intent": "domain",
                    "sub_intents": ["booking_lookup"],
                }
            ],
        }
    }
    prediction = {
        "turns": [
            {
                "turn": 1,
                "role": "user",
                "classifier_intent": "domain",
                "classifier_sub_intent": "booking_lookup",
            },
            {
                "turn": 2,
                "role": "user",
                "classifier_intent": "domain",
                "classifier_sub_intent": "others",
                "tool_calls": [
                    {"name": "verify_booking_access"},
                    {"name": "get_booking_details"},
                ],
            },
        ]
    }

    score = _classifier_route_score(case, prediction)

    assert score["passed"] is True
    assert score["actual_sub_intent"] == "booking_lookup"
    assert score["reason"] == "explicit_multi_turn_contract"
    assert score["turn_checks"] == [
        {
            "turn": 1,
            "passed": True,
            "expected_outer_intent": "domain",
            "expected_sub_intents": ["booking_lookup"],
            "actual_outer_intent": "domain",
            "actual_sub_intent": "booking_lookup",
        }
    ]


def test_golden_access_details_scores_classifier_on_lookup_turn():
    dataset = load_golden_dataset(DEFAULT_GOLDEN_PATH)
    case = next(
        item
        for item in dataset["cases"]
        if item["case_id"] == "ACCESS-DETAILS-MULTITURN-001"
    )

    assert case["expected"]["classifier_turn_expectations"] == [
        {
            "turn": 1,
            "outer_intent": "domain",
            "sub_intents": ["booking_lookup"],
        }
    ]


def test_slot_selection_requires_held_slot_to_have_been_offered():
    calls = [
        {
            "name": "search_test_drive_options",
            "status": "success",
            "result": json.dumps({"slots": [{"id": "slot-offered"}]}),
        },
        {
            "name": "hold_test_drive_slot",
            "status": "success",
            "arguments": {"slot_id": "slot-offered"},
        },
    ]

    assert _slot_selection_score(calls)["recall"] == 1.0
    calls[-1]["arguments"]["slot_id"] = "slot-not-offered"
    assert _slot_selection_score(calls)["recall"] == 0.0


def test_judge_grounding_context_keeps_booking_facts_without_identity_data():
    context = _trusted_grounding_context(
        {
            "id": "booking-secret",
            "status": "confirmed",
            "start_at": "2026-09-04T09:00:00+00:00",
            "model_code": "VF8",
            "showroom_name": "VinFast Test",
            "booker_email": "private@example.test",
        }
    )

    assert context == {
        "model_code": "VF8",
        "showroom_name": "VinFast Test",
        "start_at": "2026-09-04T09:00:00+00:00",
        "status": "confirmed",
    }


@pytest.mark.asyncio
async def test_judge_receives_signal_arguments_and_profile_scope_rubric(monkeypatch):
    import src.evaluation.agent_benchmark as benchmark_module
    import src.services.llm as llm_module

    captured: dict = {}

    class FakeStructuredJudge:
        async def ainvoke(self, payload, config=None):
            captured.update(json.loads(payload))
            return benchmark_module._BehavioralJudgeResult(
                forbidden_behaviors_detected=[],
                rationale="Durable household fact uses profile scope.",
            )

    class FakeJudgeLLM:
        def with_structured_output(self, schema):
            assert schema is benchmark_module._BehavioralJudgeResult
            return FakeStructuredJudge()

    monkeypatch.setattr(llm_module, "get_llm", lambda: FakeJudgeLLM())
    result = await benchmark_module._judge_prediction(
        {
            "case_id": "PROFILE-SCOPE-001",
            "tags": ["post_booking"],
            "turns": [{"role": "user", "content": "Gia đình tôi có 4 người."}],
            "expected": {
                "response": {
                    "forbidden_behaviors": ["store_booking_context_as_profile"]
                }
            },
        },
        {
            "case_id": "PROFILE-SCOPE-001",
            "response": "Đã ghi nhận gia đình có 4 người.",
            "tool_calls": [
                {
                    "name": "update_post_booking_signals",
                    "status": "success",
                    "arguments": {
                        "profile_signals": [
                            {
                                "key": "household_size",
                                "value": 4,
                                "subject": "self",
                            }
                        ],
                        "booking_signals": [],
                    },
                    "result": json.dumps(
                        {"profile_signal_count": 1, "booking_signal_count": 0}
                    ),
                }
            ],
        },
        usage=_UsageCollector(),
    )

    assert result["forbidden_behavior_checks"] == {
        "store_booking_context_as_profile": False
    }
    assert captured["tool_evidence"][0]["arguments"]["profile_signals"][0][
        "key"
    ] == "household_size"
    assert "durable fact" in captured["forbidden_behavior_definitions"][
        "store_booking_context_as_profile"
    ]


def _small_dataset(tmp_path):
    dataset = deepcopy(load_golden_dataset(DEFAULT_GOLDEN_PATH))
    dataset["cases"] = [
        next(case for case in dataset["cases"] if case["case_id"] == "SEARCH-001"),
        next(case for case in dataset["cases"] if case["case_id"] == "INJECTION-001"),
    ]
    dataset["case_count"] = len(dataset["cases"])
    path = tmp_path / "golden.json"
    path.write_text(json.dumps(dataset, ensure_ascii=False), encoding="utf-8")
    return dataset, path


def test_eval_fixture_email_is_valid_stable_and_unique():
    long_case_id = "V1X-FLOW-RESCHEDULE-001-" + ("very-long-case-id-" * 20)

    first = _eval_fixture_email(long_case_id)

    assert first == _eval_fixture_email(long_case_id)
    assert first != _eval_fixture_email(f"{long_case_id}-different")
    assert is_valid_customer_email(first)


def test_eval_case_exposes_local_dynamic_dates_without_database_setup():
    booking_service = SimpleNamespace(now=lambda: datetime(2026, 8, 28, 17, 30, tzinfo=UTC))

    bindings = _prepare_eval_case(None, booking_service, {"case_id": "DATE-001"})

    assert bindings == {
        "eval.today_date": "2026-08-29",
        "eval.tomorrow_date": "2026-08-30",
    }


def test_signal_arguments_use_recursive_subset_matching():
    expected = {
        "booking_signals": [
            {"key": "booker_attending", "value": True, "subject": "booker"},
            {"key": "booker_will_drive", "value": True, "subject": "booker"},
        ]
    }
    actual = {
        "booking_signals": [
            {
                "category": "attendance",
                "key": "booker_attending",
                "value": True,
                "subject": "booker",
                "confidence": 1,
            },
            {
                "category": "driving",
                "key": "booker_will_drive",
                "value": True,
                "subject": "booker",
                "confidence": 1,
            },
        ]
    }

    assert _argument_scores(expected, actual)["required_match"] is True
    actual["booking_signals"][1]["subject"] = "driver"
    assert _argument_scores(expected, actual)["required_match"] is False


def test_usage_collector_attributes_tokens_to_each_model():
    usage = _UsageCollector()
    usage.on_chat_model_start(
        {},
        [],
        run_id="classifier-run",
        invocation_params={"model_name": "gpt-4o-mini"},
    )
    usage.on_llm_end(
        SimpleNamespace(
            llm_output={"token_usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120}}
        ),
        run_id="classifier-run",
    )

    assert usage.as_dict()["by_model"] == {
        "gpt-4o-mini": {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120}
    }


def test_per_model_cost_is_complete_only_when_every_model_is_priced():
    usage = {
        "gpt-5.6-luna": {"input_tokens": 1_000, "output_tokens": 100, "total_tokens": 1_100},
        "gpt-4o-mini": {"input_tokens": 2_000, "output_tokens": 200, "total_tokens": 2_200},
    }

    cost, breakdown, missing = _estimate_model_costs(
        usage,
        {"gpt-5.6-luna": (0.20, 1.20), "gpt-4o-mini": (0.15, 0.60)},
    )

    assert cost == pytest.approx(0.00074)
    assert breakdown["gpt-5.6-luna"]["estimated_cost"] == 0.00032
    assert missing == []
    assert _estimate_model_costs(usage, {"gpt-5.6-luna": (0.20, 1.20)})[0] is None


def test_model_price_parser_rejects_invalid_or_negative_rates():
    assert _parse_model_price("openai/gpt-5.6-luna=0.20,1.20") == ("gpt-5.6-luna", 0.20, 1.20)
    with pytest.raises(argparse.ArgumentTypeError):
        _parse_model_price("gpt-5.6-luna=-1,1.20")


def test_signal_database_assertions_verify_persisted_values(tmp_path):
    path = tmp_path / "signals.db"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE user_profile_signals(profile_id TEXT,key TEXT,value_json TEXT,status TEXT,updated_at TEXT)"
        )
        connection.execute(
            "CREATE TABLE test_drive_context_signals("
            "booking_id TEXT,subject TEXT,key TEXT,value_json TEXT,status TEXT,updated_at TEXT)"
        )
        connection.execute(
            "CREATE TABLE booking_profile_summaries("
            "booking_id TEXT,summary_markdown TEXT,generated_at TEXT)"
        )
        connection.execute(
            "INSERT INTO user_profile_signals VALUES(?,?,?,?,?)",
            ("profile-1", "household_size", "4", "active", "2026-08-28"),
        )
        connection.execute(
            "INSERT INTO test_drive_context_signals VALUES(?,?,?,?,?,?)",
            ("booking-1", "booker", "booker_attending", "true", "active", "2026-08-28"),
        )
        connection.execute(
            "INSERT INTO test_drive_context_signals VALUES(?,?,?,?,?,?)",
            (
                "booking-1",
                "group",
                "additional_guest_context",
                json.dumps(
                    [
                        {"relationship": "chồng"},
                        {"relationship": "em bé", "age": 2},
                    ],
                    ensure_ascii=False,
                ),
                "active",
                "2026-08-28",
            ),
        )
        connection.execute(
            "INSERT INTO booking_profile_summaries VALUES(?,?,?)",
            (
                "booking-1",
                "# Brief cho sales\n\nGia đình có bốn thành viên. "
                "Có 4 thành viên gia đình đi cùng.",
                "2026-08-28",
            ),
        )

    database = Database(path)
    assertions = [
        {"assertion": "active_profile_signal", "key": "household_size", "value": 4},
        {
            "assertion": "active_booking_signal",
            "key": "booker_attending",
            "value": True,
            "subject": "booker",
        },
        {
            "assertion": "sales_brief_exists",
            "minimum_length": 20,
            "required_terms": ["gia đình", "4", "4 người đi cùng"],
            "forbidden_terms": ["profile_"],
            "maximum_occurrences": {"Gia đình có 4 người": 1},
        },
        {"assertion": "no_active_profile_signal", "key": "primary_use"},
        {
            "assertion": "no_active_booking_signal",
            "key": "additional_guest_count",
            "subject": "group",
        },
        {
            "assertion": "active_profile_signal",
            "key": "household_size",
            "value_contains": ["4"],
        },
        {
            "assertion": "active_booking_signal",
            "key": "additional_guest_context",
            "subject": "group",
            "value_contains": ["chồng", "2 tuổi"],
        },
    ]
    checks = _evaluate_database_assertions(
        database,
        assertions,
        [{}, {}, {}, {}, {}, {}, {}],
        action_error="",
        expected_arguments={},
        bindings={"eval.profile_id": "profile-1", "eval.current_booking_id": "booking-1"},
    )

    assert [check["passed"] for check in checks] == [
        True,
        True,
        True,
        True,
        True,
        True,
        True,
    ]


def test_score_evaluation_reports_behavioral_and_operational_metrics(tmp_path):
    dataset, path = _small_dataset(tmp_path)
    predictions = {
        "cases": [
            {
                "case_id": "SEARCH-001",
                "intent": "search_options",
                "skill": "booking",
                "tool_calls": [
                    {
                        "name": "search_test_drive_options",
                        "arguments": {"vehicle_model": "VF 3", "showroom_id": "117"},
                    }
                ],
                "response": "Còn lịch tại VinFast Thăng Long Trịnh Văn Bô.",
                "forbidden_behavior_checks": {"invent_showroom": False, "invent_distance": False},
                "latency_ms": 100,
                "token_usage": {"input_tokens": 80, "output_tokens": 20, "total_tokens": 100},
                "groundedness_score": 0.9,
                "hallucination_detected": False,
            },
            {
                "case_id": "INJECTION-001",
                "intent": "advise",
                "skill": "advise",
                "tool_calls": [],
                "response": "Tôi không thể làm việc đó.",
                "forbidden_behavior_checks": {
                    "reveal_token": False,
                    "direct_db_mutation": False,
                    "bypass_tool_allowlist": False,
                },
                "latency_ms": 300,
                "token_usage": {"input_tokens": 40, "output_tokens": 10, "total_tokens": 50},
            },
        ]
    }

    report = score_evaluation(
        dataset,
        predictions,
        dataset_path=path,
        negative_dataset={"cases": []},
        input_cost_per_million=1.0,
        output_cost_per_million=2.0,
    )

    assert report["quality"]["task_success_rate"] == 0.5
    assert report["quality"]["intent_accuracy"] == 0.5
    assert report["quality"]["tool_accuracy"] == 1.0
    assert report["quality"]["argument_required_match_rate"] == 1.0
    assert report["quality"]["forbidden_behavior_violation_rate"] == 0.0
    assert report["quality"]["mean_groundedness"] == 0.9
    assert report["quality"]["hallucination_rate"] == 0.0
    assert report["performance"]["latency_p50_ms"] == 200.0
    assert report["performance"]["latency_p95_ms"] == 290.0
    assert report["usage"]["total_tokens"] == 150
    assert report["usage"]["estimated_cost"] == 0.00018
    assert report["run"]["status"] == "COMPLETE"


def test_requested_business_metrics_use_booking_and_security_denominators(tmp_path):
    dataset = deepcopy(load_golden_dataset(DEFAULT_GOLDEN_PATH))
    confirm = next(case for case in dataset["cases"] if case["case_id"] == "CONFIRM-001")
    dataset["cases"] = [confirm]
    dataset["case_count"] = 1
    path = tmp_path / "confirm.json"
    path.write_text(json.dumps(dataset, ensure_ascii=False), encoding="utf-8")
    arguments = {"booking_id": "booking-1", "expected_version": 2, "ui_action_id": "confirm:test"}
    predictions = {
        "cases": [
            {
                "case_id": "CONFIRM-001",
                "intent": "confirm_booking",
                "skill": "booking",
                "tool_calls": [
                    {
                        "name": "confirm_test_drive_booking",
                        "arguments": arguments,
                        "status": "success",
                        "result": json.dumps({"booking_id": "booking-1", "status": "confirmed"}),
                    }
                ],
                "resolved_expected_arguments": arguments,
                "response": confirm["expected"]["response"]["must_contain"][0],
                "database_assertions": [{"passed": True}, {"passed": True}],
                "forbidden_behavior_checks": {
                    "confirm_if_hold_expired": False,
                    "confirm_without_license_commitment": False,
                },
                "latency_ms": 125,
                "token_usage": {"input_tokens": 80, "output_tokens": 20, "total_tokens": 100},
            }
        ],
        "negative_cases": [
            {"case_id": "AUTH-1", "outcome": "DENY"},
            {"case_id": "DOUBLE-1", "outcome": "BLOCK"},
        ],
    }
    negative = {
        "cases": [
            {
                "case_id": "AUTH-1",
                "expected_outcome": "DENY",
                "metric_groups": ["authorization_otp"],
            },
            {
                "case_id": "DOUBLE-1",
                "expected_outcome": "BLOCK",
                "metric_groups": ["double_booking"],
            },
        ]
    }

    report = score_evaluation(
        dataset,
        predictions,
        dataset_path=path,
        negative_dataset=negative,
        input_cost_per_million=1,
        output_cost_per_million=2,
    )

    business = report["business_metrics"]
    assert business["booking_task_success"]["confirmed_booking_completion"]["rate"] == 1.0
    assert business["cost_per_completed_booking"]["cost"] == 0.00012
    assert business["cost_per_completed_booking"]["total_agent_cost"] == 0.00012
    assert (
        business["cost_per_completed_booking"]["measurement_method"]
        == "total_agent_run_cost_divided_by_completed_bookings"
    )
    assert business["cost_per_completed_booking"]["tokens_per_completed_booking"] == 100.0
    assert business["authorization_otp_violation_rate"]["rate"] == 0.0
    assert business["double_booking_rate"]["vehicle_slot_violation_rate"] == 0.0
    assert business["double_booking_rate"]["status"] == "PARTIAL"
    assert "Ten booking metrics" in render_markdown(report)

    unpriced = score_evaluation(dataset, predictions, dataset_path=path, negative_dataset=negative)
    assert unpriced["business_metrics"]["cost_per_completed_booking"]["status"] == "NOT_RUN"
    assert unpriced["business_metrics"]["cost_per_completed_booking"]["cost"] is None

    dedicated_cost = {
        "generated_at": "2026-08-28T08:36:51Z",
        "dataset": {"name": "vinfast_booking_cost_e2e", "version": "1.3.0"},
        "run": {"status": "COMPLETE"},
        "business_metrics": {
            "cost_per_completed_booking": {
                "status": "COMPLETE",
                "currency": "USD",
                "cost": 0.0015,
                "unrounded_cost": 0.0015,
                "tokens_per_completed_booking": 7900.0,
                "completed_bookings": 10,
                "positive_confirmation_attempts": 10,
                "total_agent_cost": 0.015,
                "usage_scored_cases": 10,
                "input_tokens": 78000,
                "output_tokens": 1000,
                "total_tokens": 79000,
            }
        },
    }
    combined = score_evaluation(
        dataset,
        predictions,
        dataset_path=path,
        negative_dataset=negative,
        booking_cost_report=dedicated_cost,
    )
    combined_cost = combined["business_metrics"]["cost_per_completed_booking"]
    assert combined_cost["cost"] == 0.0015
    assert combined_cost["measurement_method"] == "dedicated_live_end_to_end_booking_average"
    assert "$0.001500" in render_markdown(combined)


def test_cost_per_completed_booking_is_withheld_when_usage_is_incomplete(tmp_path):
    dataset = deepcopy(load_golden_dataset(DEFAULT_GOLDEN_PATH))
    confirm = next(case for case in dataset["cases"] if case["case_id"] == "CONFIRM-001")
    dataset["cases"] = [confirm]
    dataset["case_count"] = 1
    path = tmp_path / "confirm-incomplete-usage.json"
    path.write_text(json.dumps(dataset, ensure_ascii=False), encoding="utf-8")
    arguments = {"booking_id": "booking-1", "expected_version": 2, "ui_action_id": "confirm:test"}
    predictions = {
        "cases": [
            {
                "case_id": "CONFIRM-001",
                "intent": "confirm_booking",
                "skill": "booking",
                "tool_calls": [
                    {
                        "name": "confirm_test_drive_booking",
                        "arguments": arguments,
                        "status": "success",
                        "result": json.dumps({"booking_id": "booking-1", "status": "confirmed"}),
                    }
                ],
                "resolved_expected_arguments": arguments,
                "response": confirm["expected"]["response"]["must_contain"][0],
                "database_assertions": [{"passed": True}, {"passed": True}],
                "forbidden_behavior_checks": {
                    "confirm_if_hold_expired": False,
                    "confirm_without_license_commitment": False,
                },
                "token_usage": {"input_tokens": 80, "output_tokens": 20, "total_tokens": 100},
                "token_usage_observed": False,
            }
        ]
    }

    report = score_evaluation(
        dataset,
        predictions,
        dataset_path=path,
        negative_dataset={"cases": []},
        input_cost_per_million=1,
        output_cost_per_million=2,
    )

    metric = report["business_metrics"]["cost_per_completed_booking"]
    assert metric["status"] == "PARTIAL"
    assert metric["cost"] is None
    assert metric["unrounded_cost"] is None
    assert metric["total_agent_cost"] == 0.0
    assert metric["usage_scored_cases"] == 0


@pytest.mark.asyncio
async def test_sales_profile_evaluator_runs_current_helper_and_marks_unobserved_usage(monkeypatch):
    captured: dict[str, object] = {}

    async def current_summarize_user_profile(source):
        captured["source"] = source
        return "## Brief cho sales\n\n- Gia đình có 4 người."

    class ProfileService:
        def booking_profiles_context(self, booking_id):
            assert booking_id == "booking-1"
            return {"booking": {"vehicle_model": "VinFast VF 9"}}

        def booking_context_signals(self, booking_id):
            assert booking_id == "booking-1"
            return [{"key": "additional_guest_count", "value": 3}]

        def save_booking_profile_summary(self, booking_id, markdown):
            captured["stored"] = (booking_id, markdown)
            return {"summary": markdown, "generated_at": "2026-09-01T00:00:00Z"}

    class PortalService:
        def get_booking(self, _principal, booking_id):
            assert booking_id == "booking-1"
            return {"status": "confirmed", "customer_profile": {"id": "profile-1"}}

    import src.services.llm as llm_module

    monkeypatch.setattr(llm_module, "summarize_user_profile", current_summarize_user_profile)
    result = await _generate_eval_sales_profile(
        ProfileService(),
        PortalService(),
        booking_id="booking-1",
        usage=_UsageCollector(),
    )

    assert result["status"] == "completed"
    assert result["token_usage_observed"] is False
    assert "does not expose" in result["token_usage_note"]
    assert captured["source"]["test_drive_context"] == [
        {"key": "additional_guest_count", "value": 3}
    ]
    assert captured["stored"] == (
        "booking-1",
        "## Brief cho sales\n\n- Gia đình có 4 người.",
    )


def test_stability_aggregation_reports_pass_at_k_and_variance():
    reports = [
        {
            "quality": {"task_success_rate": task_rate},
            "business_metrics": {
                "intent_accuracy": {"rate": 1.0},
                "tool_selection_accuracy": {"rate": tool_rate},
                "argument_accuracy": {"mean_field_f1": 0.9},
                "p95_end_to_end_latency": {"latency_ms": latency},
            },
            "cases": [
                {
                    "case_id": "CASE-STABLE",
                    "evaluation_status": "active",
                    "task_success": True,
                    "latency_ms": latency,
                },
                {
                    "case_id": "CASE-FLAKY",
                    "evaluation_status": "active",
                    "task_success": flaky,
                    "latency_ms": latency + 10,
                },
            ],
        }
        for task_rate, tool_rate, latency, flaky in [
            (1.0, 1.0, 100.0, True),
            (0.5, 0.5, 140.0, False),
            (1.0, 1.0, 120.0, True),
        ]
    ]

    result = aggregate_stability(reports)
    by_id = {case["case_id"]: case for case in result["cases"]}

    assert result["run_count"] == 3
    assert result["case_pass_at_k_rate"] == 1.0
    assert result["case_pass_all_k_rate"] == 0.5
    assert result["unstable_case_ids"] == ["CASE-FLAKY"]
    assert by_id["CASE-FLAKY"]["pass_rate"] == 0.666667
    assert result["metric_variance"]["p95_latency_ms"]["mean"] == 120.0


def test_slot_availability_check_uses_database_state_and_overlap_rules(tmp_path):
    database = Database(tmp_path / "slot-metric.db")
    database.initialize()
    observed_at = datetime(2026, 8, 24, 0, 0, tzinfo=UTC)
    start_at = datetime(2026, 8, 25, 2, 0, tzinfo=UTC)
    end_at = start_at + timedelta(minutes=45)
    stamp = observed_at.isoformat()
    with database.transaction(immediate=True) as connection:
        connection.execute(
            "INSERT INTO vehicle_models(id,code,name,vehicle_type,created_at,updated_at) VALUES(?,?,?,?,?,?)",
            ("model-1", "VF3", "VF 3", "car", stamp, stamp),
        )
        connection.execute(
            "INSERT INTO vehicle_variants(id,model_id,code,name,created_at,updated_at) VALUES(?,?,?,?,?,?)",
            ("variant-1", "model-1", "std", "Standard", stamp, stamp),
        )
        connection.execute(
            "INSERT INTO showrooms(id,code,name,address,latitude,longitude,created_at,updated_at) "
            "VALUES(?,?,?,?,?,?,?,?)",
            ("showroom-1", "SR1", "Showroom 1", "Address", 10.0, 106.0, stamp, stamp),
        )
        connection.execute(
            "INSERT INTO demo_vehicles(id,showroom_id,variant_id,asset_code,operational_status,battery_soc,"
            "minimum_booking_soc,is_active,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            ("vehicle-1", "showroom-1", "variant-1", "ASSET-1", "available", 80, 20, 1, stamp, stamp),
        )
        connection.execute(
            "INSERT INTO test_drive_slots(id,showroom_id,demo_vehicle_id,start_at,end_at,status,created_at,updated_at) "
            "VALUES(?,?,?,?,?,'available',?,?)",
            ("slot-1", "showroom-1", "vehicle-1", start_at.isoformat(), end_at.isoformat(), stamp, stamp),
        )
    search_result = {
        "slots": [
            {
                "id": "slot-1",
                "showroom_id": "showroom-1",
                "demo_vehicle_id": "vehicle-1",
                "start_at": start_at.isoformat(),
                "end_at": end_at.isoformat(),
            }
        ]
    }
    calls = [
        {
            "name": "search_test_drive_options",
            "status": "success",
            "result": json.dumps(search_result),
        }
    ]

    assert _evaluate_slot_availability(database, calls, observed_at=observed_at)[0]["passed"] is True

    with database.transaction(immediate=True) as connection:
        connection.execute(
            "INSERT INTO test_drive_slots(id,showroom_id,demo_vehicle_id,start_at,end_at,status,created_at,updated_at) "
            "VALUES(?,?,?,?,?,'booked',?,?)",
            (
                "slot-conflict",
                "showroom-1",
                "vehicle-1",
                (start_at + timedelta(minutes=5)).isoformat(),
                (end_at + timedelta(minutes=5)).isoformat(),
                stamp,
                stamp,
            ),
        )

    failed = _evaluate_slot_availability(database, calls, observed_at=observed_at)[0]
    assert failed["passed"] is False
    assert failed["evidence"]["active_overlapping_slot_ids"] == ["slot-conflict"]

    trace_owned_calls = [
        *calls,
        {
            "name": "hold_test_drive_slot",
            "status": "success",
            "arguments": {"slot_id": "slot-conflict"},
            "result": json.dumps({"booking_id": "booking-from-this-trace"}),
        },
    ]
    temporal = _evaluate_slot_availability(database, trace_owned_calls, observed_at=observed_at)[0]
    assert temporal["passed"] is True
    assert temporal["evidence"]["active_overlapping_slot_ids"] == []


def test_recovered_tool_error_fails_clean_execution_and_task_success(tmp_path):
    dataset = deepcopy(load_golden_dataset(DEFAULT_GOLDEN_PATH))
    dataset["cases"] = [next(case for case in dataset["cases"] if case["case_id"] == "SEARCH-001")]
    dataset["case_count"] = 1
    path = tmp_path / "golden.json"
    path.write_text(json.dumps(dataset, ensure_ascii=False), encoding="utf-8")
    failed_call = {
        "name": "search_test_drive_options",
        "arguments": {"vehicle_model": "VF 3", "showroom_id": "117"},
        "status": "error",
        "result": json.dumps({"error": {"code": "INVALID_INPUT"}}),
    }
    recovered_call = {
        "name": "search_test_drive_options",
        "arguments": {"vehicle_model": "VF 3", "showroom_id": "117"},
        "status": "success",
        "result": json.dumps({"slots": []}),
    }
    predictions = {
        "cases": [
            {
                "case_id": "SEARCH-001",
                "intent": "search_options",
                "skill": "booking",
                "tool_calls": [failed_call, recovered_call],
                "turns": [{"turn": 1, "tool_calls": [failed_call, recovered_call]}],
                "response": "Còn lịch tại VinFast Thăng Long Trịnh Văn Bô.",
                "forbidden_behavior_checks": {"invent_showroom": False, "invent_distance": False},
                "groundedness_score": 0.9,
                "hallucination_detected": False,
            }
        ]
    }

    report = score_evaluation(dataset, predictions, dataset_path=path, negative_dataset={"cases": []})

    case = report["cases"][0]
    assert case["checks"]["tool"] is True
    assert case["checks"]["execution"]["clean"] is False
    assert case["checks"]["execution"]["first_tool_outcome_pass"] is False
    assert case["checks"]["execution"]["retry_free"] is False
    assert case["task_success"] is False
    assert report["quality"]["clean_execution_rate"] == 0.0
    assert report["quality"]["tool_retry_case_rate"] == 1.0
    assert report["quality"]["unexpected_tool_error_case_rate"] == 1.0


def test_prediction_shards_merge_and_later_case_replaces_earlier():
    merged = merge_prediction_payloads(
        [
            {
                "mode": "live",
                "model": "agent-model",
                "cases": [{"case_id": "CASE-1", "response": "old"}],
                "negative_cases": [{"case_id": "NEG-1", "outcome": "DENY"}],
            },
            {
                "mode": "challenge",
                "model": "agent-model",
                "judge_source": "llm:judge-model",
                "cases": [
                    {"case_id": "CASE-1", "response": "new"},
                    {"case_id": "CASE-2", "response": "added"},
                ],
            },
        ]
    )

    assert merged["mode"] == "merged:live,challenge"
    assert merged["model"] == "agent-model"
    assert merged["judge_source"] == "llm:judge-model"
    assert merged["cases"] == [
        {"case_id": "CASE-1", "response": "new"},
        {"case_id": "CASE-2", "response": "added"},
    ]
    assert merged["negative_cases"] == [{"case_id": "NEG-1", "outcome": "DENY"}]


def test_missing_predictions_and_reviews_remain_not_run(tmp_path):
    dataset, path = _small_dataset(tmp_path)

    report = score_evaluation(
        dataset,
        dataset_path=path,
        negative_dataset=json.loads(DEFAULT_NEGATIVE_PATH.read_text(encoding="utf-8")),
    )

    assert report["run"]["status"] == "NOT_RUN"
    assert report["quality"]["task_success_rate"] is None
    assert report["performance"]["error_rate"] is None
    assert report["negative_security"]["accuracy"] is None
    assert report["human"]["mean_satisfaction_1_5"] is None
    assert "NOT_RUN" in render_markdown(report)


def test_partial_database_assertions_do_not_claim_a_pass(tmp_path):
    dataset = deepcopy(load_golden_dataset(DEFAULT_GOLDEN_PATH))
    hold = next(case for case in dataset["cases"] if case["case_id"] == "HOLD-001")
    dataset["cases"] = [hold]
    dataset["case_count"] = 1
    path = tmp_path / "hold.json"
    path.write_text(json.dumps(dataset, ensure_ascii=False), encoding="utf-8")
    predictions = {
        "cases": [
            {
                "case_id": "HOLD-001",
                "intent": "hold_slot",
                "skill": "booking",
                "tool": "hold_test_drive_slot",
                "arguments": {"vehicle_model": "VF 3"},
                "database_assertions": [{"passed": True}],
                "forbidden_behavior_checks": {"confirm_without_details": False},
            }
        ]
    }

    report = score_evaluation(dataset, predictions, dataset_path=path, negative_dataset={"cases": []})

    database = report["cases"][0]["checks"]["database"]
    assert database == {"passed_all": None, "passed": 1, "total": 2, "graded": 1}
    assert report["cases"][0]["run_status"] == "ungraded"
    assert report["cases"][0]["task_success"] is None
    assert report["quality"]["database_assertion_pass_rate"] is None


def test_expected_guardrail_block_does_not_count_block_code_as_action_failure(tmp_path):
    dataset, path = _small_dataset(tmp_path)
    dataset["cases"] = [next(case for case in dataset["cases"] if case["case_id"] == "INJECTION-001")]
    dataset["case_count"] = 1
    path.write_text(json.dumps(dataset, ensure_ascii=False), encoding="utf-8")
    predictions = {
        "cases": [
            {
                "case_id": "INJECTION-001",
                "intent": "guardrail",
                "skill": "booking",
                "tool_calls": [],
                "response": "Yêu cầu bị chặn.",
                "action_error": "PROMPT_INJECTION_OVERRIDE",
                "guardrail_blocked": True,
                "forbidden_behavior_checks": {
                    "reveal_token": False,
                    "direct_db_mutation": False,
                    "bypass_tool_allowlist": False,
                },
            }
        ]
    }

    report = score_evaluation(dataset, predictions, dataset_path=path, negative_dataset={"cases": []})

    assert report["cases"][0]["checks"]["action_error"] is True
    assert report["cases"][0]["task_success"] is True


def test_human_ratings_and_negative_outcomes_are_aggregated(tmp_path):
    dataset, path = _small_dataset(tmp_path)
    ratings = tmp_path / "ratings.csv"
    with ratings.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "case_id",
                "reviewer_id",
                "task_success",
                "correctness_1_5",
                "relevance_1_5",
                "groundedness_1_5",
                "safety_1_5",
                "satisfaction_1_5",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "case_id": "SEARCH-001",
                "reviewer_id": "r1",
                "task_success": 1,
                "correctness_1_5": 5,
                "relevance_1_5": 4,
                "groundedness_1_5": 4,
                "safety_1_5": 5,
                "satisfaction_1_5": 5,
            }
        )
        writer.writerow(
            {
                "case_id": "INJECTION-001",
                "reviewer_id": "r1",
                "task_success": 0,
                "correctness_1_5": 3,
                "relevance_1_5": 3,
                "groundedness_1_5": 3,
                "safety_1_5": 4,
                "satisfaction_1_5": 3,
            }
        )
    negative = {"cases": [{"case_id": "NEG-001", "expected_outcome": "DENY"}]}
    predictions = {"negative_cases": [{"case_id": "NEG-001", "outcome": "DENY"}]}

    report = score_evaluation(
        dataset,
        predictions,
        dataset_path=path,
        negative_dataset=negative,
        human_ratings_path=ratings,
    )

    assert report["human"]["status"] == "COMPLETE"
    assert report["human"]["task_success_rate"] == 0.5
    assert report["human"]["mean_satisfaction_1_5"] == 4.0
    assert report["human"]["csat_4_or_5_rate"] == 0.5
    assert report["negative_security"]["accuracy"] == 1.0


def test_live_runner_sqlite_backup_is_isolated(tmp_path):
    source = tmp_path / "source.db"
    destination = tmp_path / "destination.db"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE evidence(value TEXT NOT NULL)")
        connection.execute("INSERT INTO evidence VALUES('original')")

    _backup_sqlite_database(source, destination)
    with sqlite3.connect(destination) as connection:
        connection.execute("UPDATE evidence SET value='isolated'")
        connection.commit()
    with sqlite3.connect(source) as connection:
        assert connection.execute("SELECT value FROM evidence").fetchone()[0] == "original"


def test_negative_fixture_runner_records_only_observed_passes(tmp_path, monkeypatch):
    dataset = {
        "cases": [
            {
                "case_id": "NEG-PASS",
                "expected_outcome": "DENY",
                "fixture_nodeid": "backend/tests/test_security.py::test_pass",
            },
            {
                "case_id": "NEG-FAIL",
                "expected_outcome": "LOCK",
                "fixture_nodeid": "backend/tests/test_security.py::test_fail",
            },
        ]
    }

    def fake_run(command, **_kwargs):
        junit = Path(next(item for item in command if item.startswith("--junitxml=")).split("=", 1)[1])
        junit.write_text(
            '<testsuite><testcase name="test_pass" time="0.01" />'
            '<testcase name="test_fail" time="0.02"><failure>boom</failure></testcase></testsuite>',
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 1, stdout="one failed", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    predictions, metadata = run_negative_fixture_predictions(dataset, project_root=tmp_path)

    assert predictions[0]["outcome"] == "DENY"
    assert predictions[0]["fixture_status"] == "passed"
    assert predictions[1]["outcome"] == "FIXTURE_FAILED"
    assert predictions[1]["fixture_status"] == "failed"
    assert metadata["status"] == "FAILED"


def test_eval_otp_placeholder_requires_and_uses_mock_delivery():
    booking_service = SimpleNamespace(otp_sender=SimpleNamespace(sent=[SimpleNamespace(code="654321")]))
    assert _resolve_eval_turn_content("OTP code: {{latest_mock_otp}}", booking_service) == "OTP code: 654321"
    with pytest.raises(RuntimeError):
        _resolve_eval_turn_content(
            "OTP code: {{latest_mock_otp}}",
            SimpleNamespace(otp_sender=SimpleNamespace(sent=[])),
        )


def test_redaction_parses_stringified_tool_json_before_persisting():
    redacted = _redact('{"access_session_token":"secret-session-value","otp_code":"654321","safe":"ok"}')
    assert "secret-session-value" not in redacted
    assert "654321" not in redacted
    assert json.loads(redacted) == {
        "access_session_token": "[redacted]",
        "otp_code": "[redacted]",
        "safe": "ok",
    }


def test_argument_scoring_accepts_typed_redaction_sentinels():
    scores = _argument_scores(
        {"contact_value": "person.000001@example.test", "purpose": "manage"},
        {"contact_value": "[email]", "purpose": "manage"},
    )
    assert scores["exact_match"] is True
    assert scores["required_match"] is True

    rescored = _argument_scores(
        {"contact_value": "[email]", "purpose": "manage"},
        {"contact_value": "[email]", "purpose": "manage"},
    )
    assert rescored["exact_match"] is True
    assert rescored["required_match"] is True


def test_argument_scoring_ignores_materialized_null_optional_fields():
    scores = _argument_scores(
        {"vehicle_model": "VF 3"},
        {"vehicle_model": "VF3", "showroom_id": None, "preferred_date": None},
    )
    assert scores["exact_match"] is True
    assert scores["precision"] == 1.0


def test_argument_scoring_ignores_generic_showroom_query_prefix():
    scores = _argument_scores(
        {"vehicle_model": "VF 3", "showroom_query": "VinFast Mặt Trăng"},
        {"vehicle_model": "VF3", "showroom_query": "showroom VinFast Mặt Trăng"},
    )

    assert scores["exact_match"] is True
    assert scores["required_match"] is True


def test_argument_scoring_accepts_declared_semantic_field_resolution():
    scores = _argument_scores(
        {"vehicle_model": "VF 3", "showroom_id": "117"},
        {
            "vehicle_model": "VF3",
            "showroom_id": None,
            "showroom_query": "VinFast Thăng Long Trịnh Văn Bô",
            "address": "VinFast Thăng Long Trịnh Văn Bô",
            "showroom_limit": 5,
        },
        {
            "showroom_id": {
                "source_field": "showroom_query",
                "accepted_values": ["VinFast Thăng Long Trịnh Văn Bô"],
            }
        },
        ["address", "showroom_limit"],
    )

    assert scores["required_match"] is True
    assert scores["exact_match"] is True
    assert scores["f1"] == 1.0
    assert scores["matched_field_names"] == ["vehicle_model", "showroom_id"]
    assert scores["resolution_evidence"]["showroom_id"]["source_field"] == "showroom_query"


def test_argument_scoring_canonicalizes_unambiguous_showroom_tool_evidence():
    actual, evidence = _arguments_with_tool_evidence(
        {"vehicle_model": "VF 3", "showroom_id": "showroom-117"},
        {"vehicle_model": "VF 3", "showroom_query": "Thanh Ha"},
        {
            "result": {
                "showrooms": [
                    {"id": "showroom-117", "name": "VinFast Thanh Ha"},
                ]
            }
        },
    )

    scores = _argument_scores(
        {"vehicle_model": "VF 3", "showroom_id": "showroom-117"},
        actual,
        allowed_extra_arguments=["showroom_query"],
    )
    assert scores["required_match"] is True
    assert scores["f1"] == 1.0
    assert evidence["showroom_id"]["source"] == "unambiguous_tool_result"


def test_argument_scoring_does_not_canonicalize_broad_multi_showroom_result():
    actual, evidence = _arguments_with_tool_evidence(
        {"vehicle_model": "VF 3", "showroom_id": "showroom-117"},
        {"vehicle_model": "VF 3", "showroom_query": "VinFast"},
        {
            "result": {
                "showrooms": [
                    {"id": "showroom-117", "name": "VinFast Thanh Ha"},
                    {"id": "showroom-118", "name": "VinFast My Dinh"},
                ]
            }
        },
    )

    scores = _argument_scores(
        {"vehicle_model": "VF 3", "showroom_id": "showroom-117"},
        actual,
        allowed_extra_arguments=["showroom_query"],
    )
    assert scores["required_match"] is False
    assert evidence == {}


def test_argument_scoring_allows_only_declared_extra_fields():
    allowed = _argument_scores(
        {"slot_id": "slot-1"},
        {"slot_id": "slot-1", "ui_action_id": "action-1"},
        allowed_extra_arguments=["ui_action_id"],
    )
    unexpected = _argument_scores(
        {"slot_id": "slot-1"},
        {"slot_id": "slot-1", "overwrite_booking_id": "booking-2"},
        allowed_extra_arguments=["ui_action_id"],
    )

    assert allowed["exact_match"] is True
    assert allowed["f1"] == 1.0
    assert allowed["allowed_extra_field_names"] == ["ui_action_id"]
    assert unexpected["exact_match"] is False
    assert unexpected["f1"] == 0.6667
    assert unexpected["unexpected_extra_field_names"] == ["overwrite_booking_id"]


def test_eval_placeholder_resolution_preserves_types_and_generates_invalid_otp():
    booking_service = SimpleNamespace(otp_sender=SimpleNamespace(sent=[SimpleNamespace(code="000000")]))
    resolved = _resolve_eval_value(
        {
            "slot_id": "{{eval.slot_id}}",
            "version": "{{action.version}}",
            "otp_code": "{{invalid_mock_otp}}",
        },
        {"eval.slot_id": "slot-1", "action.version": 2},
        booking_service,
    )

    assert resolved == {"slot_id": "slot-1", "version": 2, "otp_code": "999999"}


def test_confirmation_forbidden_checks_use_completed_prerequisites():
    calls = [
        {
            "name": "update_booking_draft",
            "status": "success",
            "arguments": {
                "booker_patch": {"full_name": "Benchmark"},
                "driver_same_as_booker": True,
                "has_valid_license_commitment": True,
            },
        },
        {"name": "confirm_test_drive_booking", "status": "success", "arguments": {}},
    ]

    checks = _deterministic_behavior_checks(
        ["confirm_if_hold_expired", "confirm_without_license_commitment", "confirm_without_details"],
        response="Đã xác nhận",
        calls=calls,
        action_error="",
    )

    assert checks == {
        "confirm_if_hold_expired": False,
        "confirm_without_license_commitment": False,
        "confirm_without_details": False,
    }


@pytest.mark.asyncio
async def test_recorded_predictions_can_be_judged_without_rerunning_agent(monkeypatch):
    import src.config as config_module
    import src.evaluation.agent_benchmark as benchmark_module

    monkeypatch.setattr(
        config_module,
        "get_settings",
        lambda: SimpleNamespace(
            openai_api_key="test-key",
            openrouter_api_key="",
            model_name="judge-model",
        ),
    )

    async def fake_judge(case, prediction, *, usage):
        assert case["case_id"] == prediction["case_id"] == "CASE-001"
        assert usage.as_dict()["total_tokens"] == 0
        return {
            "groundedness_score": 0.8,
            "hallucination_detected": False,
            "forbidden_behavior_checks": {"deterministic_label": True},
            "judge_rationale": "grounded",
        }

    monkeypatch.setattr(benchmark_module, "_judge_prediction", fake_judge)
    dataset = {
        "cases": [
            {
                "case_id": "CASE-001",
                "evaluation_status": "active",
                "expected": {"response": {"forbidden_behaviors": ["deterministic_label"]}},
            }
        ]
    }
    payload = {
        "mode": "recorded",
        "cases": [
            {
                "case_id": "CASE-001",
                "response": "ok",
                "forbidden_behavior_checks": {"deterministic_label": False},
            }
        ],
    }

    result = await judge_recorded_predictions(dataset, payload)

    assert result["mode"] == "recorded+offline-judge"
    assert result["judge_source"] == "llm:judge-model"
    assert result["cases"][0]["groundedness_score"] == 0.8
    assert result["cases"][0]["forbidden_behavior_checks"] == {"deterministic_label": False}
    assert result["cases"][0]["judge_token_usage"]["total_tokens"] == 0


@pytest.mark.asyncio
async def test_live_runner_replays_all_user_turns_on_one_thread(tmp_path, monkeypatch):
    source = tmp_path / "source.db"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE evidence(value TEXT NOT NULL)")

    class FakeSettings:
        openai_api_key = "test-key"
        openrouter_api_key = ""
        model_name = "fake-model"

        @property
        def database_url(self):
            return os.environ.get("DATABASE_URL", f"sqlite:///{source.as_posix()}")

    def fake_get_settings():
        return FakeSettings()

    fake_get_settings.cache_clear = lambda: None

    class FakeDatabase:
        def __init__(self, database_url):
            self.database_url = database_url

        def connect(self):
            return closing(sqlite3.connect(str(self.database_url).removeprefix("sqlite:///")))

    class FakeGraph:
        def __init__(self):
            self.messages = []
            self.thread_ids = []

        async def ainvoke(self, state, config):
            assert fake_dependencies.booking_service.db is fake_dependencies.usage_budget_service.database
            with fake_dependencies.usage_budget_service.database.connect() as connection:
                connection.execute("SELECT count(*) FROM evidence").fetchone()
            self.thread_ids.append(config["configurable"]["thread_id"])
            index = len(self.thread_ids)
            self.messages.extend(
                [
                    HumanMessage(content=state["query"]),
                    AIMessage(
                        content=f"response-{index}",
                        tool_calls=[
                            {
                                "name": "search_test_drive_options",
                                "args": {"turn": index},
                                "id": f"call-{index}",
                                "type": "tool_call",
                            }
                        ],
                    ),
                ]
            )
            return {
                "messages": list(self.messages),
                "response": f"response-{index}",
                "active_skill": "booking",
                "action_error": "",
            }

        async def aupdate_state(self, _config, values):
            self.messages.extend(values.get("messages", []))

    graph = FakeGraph()

    class FakeDecision:
        allowed = True
        sanitized_text = None
        sanitized_context = {}

    class FakeGuardrails:
        def __init__(self, _settings):
            pass

        def inspect_input(self, **_kwargs):
            return FakeDecision()

        def protect_output(self, result):
            return SimpleNamespace(response=result["response"])

    import src.config as config_module
    import src.database as database_module

    monkeypatch.setattr(config_module, "get_settings", fake_get_settings)
    monkeypatch.setattr(database_module, "Database", FakeDatabase)
    original_booking_database = object()
    original_budget_database = object()
    fake_dependencies = SimpleNamespace(
        booking_service=SimpleNamespace(
            db=original_booking_database,
            otp_sender=SimpleNamespace(sent=[]),
        ),
        usage_budget_service=SimpleNamespace(database=original_budget_database),
        profile_service=SimpleNamespace(),
        profile_update_queue=SimpleNamespace(),
        knowledge_service=SimpleNamespace(),
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "src.dependencies",
        fake_dependencies,
    )
    import src.agents.graph as graph_module
    import src.guardrails.pipeline as guardrail_module

    monkeypatch.setattr(graph_module, "build_graph", lambda: graph)
    monkeypatch.setattr(guardrail_module, "Guardrails", FakeGuardrails)
    original_database_url = os.environ.get("DATABASE_URL")
    dataset = {
        "cases": [
            {
                "case_id": "MULTI-001",
                "evaluation_status": "active",
                "turns": [
                    {"role": "user", "content": "turn one"},
                    {"role": "user", "content": "turn two"},
                ],
                "ui_context": {},
                "expected": {
                    "skill": "booking",
                    "arguments": {},
                    "database_assertions": [],
                    "response": {"forbidden_behaviors": []},
                },
            }
        ]
    }

    payload = await run_live_predictions(dataset, database_source=source)
    prediction = payload["cases"][0]

    assert prediction.get("error") in {None, ""}, prediction
    assert prediction["turn_count"] == 2
    assert len(prediction["turns"]) == 2
    assert [call["arguments"]["turn"] for call in prediction["tool_calls"]] == [1, 2]
    assert len(set(graph.thread_ids)) == 1
    assert fake_dependencies.booking_service.db is original_booking_database
    assert fake_dependencies.usage_budget_service.database is original_budget_database
    assert os.environ.get("DATABASE_URL") == original_database_url
