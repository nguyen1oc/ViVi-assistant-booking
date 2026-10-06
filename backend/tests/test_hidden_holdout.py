from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from src.evaluation.holdout import (
    REQUIRED_MUTATION_CATEGORIES,
    build_public_summary,
    claim_one_shot_lock,
    human_review_gate,
    validate_hidden_holdout,
)


def _case(case_id: str, category: str, prompt: str, source: str = "REG-001") -> dict:
    return {
        "case_id": case_id,
        "source_case_ids": [source],
        "mutation_category": category,
        "turns": [{"role": "user", "content": prompt}],
        "expected": {"intent": "search_options", "skill": "booking", "tool": "search_test_drive_options"},
        "tags": ["hidden_holdout", f"mutation:{category}"],
        "review_status": "FROZEN_HOLDOUT_NOT_HUMAN_REVIEWED",
        "evaluation_status": "active",
    }


def _datasets() -> tuple[dict, dict]:
    regression = {
        "case_count": 1,
        "cases": [
            {
                "case_id": "REG-001",
                "turns": [{"role": "user", "content": "regression prompt"}],
            }
        ],
    }
    cases = [
        _case(f"HOLDOUT-{index:03d}", category, f"new prompt {category}")
        for index, category in enumerate(REQUIRED_MUTATION_CATEGORIES, start=1)
    ]
    holdout = {
        "split": "hidden_holdout",
        "case_count": len(cases),
        "mutation_category_counts": {category: 1 for category in REQUIRED_MUTATION_CATEGORIES},
        "cases": cases,
    }
    return regression, holdout


def _report(case_ids: list[str], successes: list[bool]) -> dict:
    passed = sum(successes)
    return {
        "dataset": {"active_cases": len(case_ids)},
        "run": {"status": "COMPLETE"},
        "quality": {
            "task_success_rate": passed / len(case_ids),
            "task_success_scored_cases": len(case_ids),
            "task_success_confidence_interval_95": {"lower": 0.1, "upper": 0.9},
            "intent_accuracy": 1.0,
            "tool_accuracy": 1.0,
            "argument_mean_field_f1": 1.0,
        },
        "performance": {"latency_p95_ms": 1000},
        "cases": [
            {"case_id": case_id, "task_success": success} for case_id, success in zip(case_ids, successes, strict=True)
        ],
    }


def test_hidden_holdout_validation_requires_isolated_six_category_split():
    regression, holdout = _datasets()
    assert validate_hidden_holdout(holdout, regression, expected_regression_count=1) == {
        category: 1 for category in REQUIRED_MUTATION_CATEGORIES
    }

    duplicate = deepcopy(holdout)
    duplicate["cases"][0]["case_id"] = "REG-001"
    with pytest.raises(ValueError, match="overlaps regression"):
        validate_hidden_holdout(duplicate, regression, expected_regression_count=1)


def test_one_shot_lock_cannot_be_claimed_twice(tmp_path: Path):
    lock = tmp_path / "frozen.json"
    claim_one_shot_lock(lock, {"attempt_count": 1})
    with pytest.raises(FileExistsError):
        claim_one_shot_lock(lock, {"attempt_count": 2})


def test_human_gate_requires_two_complete_reviews_for_every_split_case(tmp_path: Path):
    ratings = tmp_path / "reviews.csv"
    ratings.write_text(
        "case_id,reviewer_id,task_success,correctness_1_5,relevance_1_5,groundedness_1_5,safety_1_5,satisfaction_1_5\n"
        "REG-001,a,1,5,5,5,5,5\n"
        "REG-001,b,1,5,5,5,5,5\n"
        "HOLDOUT-001,a,1,5,5,5,5,5\n",
        encoding="utf-8",
    )
    gate = human_review_gate(["REG-001"], ["HOLDOUT-001"], [ratings])
    assert gate["status"] == "PARTIAL"
    assert gate["sufficient_for_overall"] is False


def test_public_summary_withholds_overall_until_human_gate_is_complete(tmp_path: Path):
    regression, holdout = _datasets()
    regression_report = _report(["REG-001"], [True])
    holdout_ids = [case["case_id"] for case in holdout["cases"]]
    holdout_report = _report(holdout_ids, [True, True, False, True, True, True])
    summary = build_public_summary(
        regression_dataset=regression,
        regression_report=regression_report,
        holdout_dataset=holdout,
        holdout_report=holdout_report,
        ratings_paths=[tmp_path / "missing.csv"],
        freeze={"status": "COMPLETED", "attempt_count": 1},
    )
    assert summary["splits"]["regression"]["task_success_rate"] == 1.0
    assert summary["splits"]["hidden_holdout"]["task_success_rate"] == pytest.approx(5 / 6)
    assert summary["overall"]["status"] == "WITHHELD_HUMAN_REVIEW_INSUFFICIENT"
    assert summary["overall"]["task_success_rate"] is None
    assert "withheld_candidate_rate" not in summary["overall"]
    json.dumps(summary)
