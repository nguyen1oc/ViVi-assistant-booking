import json
from collections import Counter
from copy import deepcopy
from types import SimpleNamespace

import pytest
import src.evaluation.guardrail_benchmark as benchmark_module
from src.evaluation.guardrail_benchmark import (
    DEFAULT_DATASET_PATH,
    load_dataset,
    render_markdown,
    run_benchmark,
    verify_baseline,
)
from src.guardrails import input_guard as input_guard_module
from src.guardrails.models import GuardrailDecision
from src.guardrails.output_guard import OutputGuard
from src.guardrails.untrusted_content import UntrustedContentGuard


def _failed_case_ids(report):
    return {case["case_id"] for case in report["cases"] if not case["passed"]}


def test_guardrail_benchmark_dataset_is_valid_unique_and_balanced():
    dataset = load_dataset(DEFAULT_DATASET_PATH)
    cases = dataset["cases"]
    category_counts = Counter(case["category"] for case in cases)
    category_minimums = dataset["coverage_policy"]["minimum_cases_by_category"]

    assert dataset["schema_version"] == "1.2"
    assert dataset["case_count"] == len(cases) == 93
    assert len({case["case_id"] for case in cases}) == len(cases)
    assert {case["kind"] for case in cases} == {
        "abuse",
        "conversation",
        "input",
        "output",
        "rate_limit",
        "tool",
        "untrusted_content",
    }
    assert set(category_counts) == set(category_minimums)
    assert min(category_minimums.values()) >= 2
    assert all(category_counts[category] >= minimum for category, minimum in category_minimums.items())
    assert sum(case["kind"] == "input" for case in cases) >= 30
    assert sum(case["kind"] == "output" for case in cases) >= 10
    assert sum(case["kind"] == "tool" for case in cases) >= 10
    assert any("false-positive" in case.get("tags", []) for case in cases)
    assert any("negation" in case.get("tags", []) for case in cases)


def test_every_guardrail_benchmark_case_passes_as_a_ci_regression_gate():
    report = run_benchmark(load_dataset(DEFAULT_DATASET_PATH))

    assert report["summary"]["total"] == 93
    assert report["summary"]["failed"] == 0
    assert report["summary"]["pass_rate"] == 1.0
    assert report["coverage_gate"]["passed"] is True
    assert report["coverage_gate"]["category_count"] == 30
    assert report["quality_metrics"]["attack_block_accuracy"] == 1.0
    assert report["quality_metrics"]["benign_allow_accuracy"] == 1.0
    assert report["quality_metrics"]["output_protection_accuracy"] == 1.0


def test_benchmark_filters_are_deterministic_and_report_is_reviewable():
    dataset = load_dataset(DEFAULT_DATASET_PATH)
    report = run_benchmark(dataset, kinds={"tool"}, tags={"confirmation"})
    markdown = render_markdown(report)

    assert report["summary"]["total"] == 8
    assert report["summary"]["failed"] == 0
    assert set(report["case_distribution"]) == {"tool"}
    assert "# Guardrail Benchmark Report" in markdown
    assert "No failed cases." in markdown
    assert "deterministic, offline policy benchmark" in markdown


def test_committed_baseline_matches_the_current_dataset():
    report = run_benchmark(load_dataset(DEFAULT_DATASET_PATH))
    baseline_path = DEFAULT_DATASET_PATH.parent / "results" / "baseline.json"

    assert verify_baseline(report, baseline_path) == []


def test_baseline_verification_rejects_stale_dataset_hash(tmp_path):
    report = run_benchmark(load_dataset(DEFAULT_DATASET_PATH))
    stale = deepcopy(report)
    stale["dataset_sha256"] = "stale-dataset-hash"
    path = tmp_path / "stale-baseline.json"
    path.write_text(json.dumps(stale, ensure_ascii=False), encoding="utf-8")

    failures = verify_baseline(report, path)

    assert "dataset_sha256 does not match the current benchmark" in failures


def test_benchmark_covers_conversation_binding_and_rate_limiting():
    report = run_benchmark(
        load_dataset(DEFAULT_DATASET_PATH),
        kinds={"conversation", "rate_limit"},
    )

    assert report["summary"]["total"] == 4
    assert report["summary"]["failed"] == 0


def test_benchmark_covers_persistent_three_strike_abuse_ban():
    report = run_benchmark(load_dataset(DEFAULT_DATASET_PATH), kinds={"abuse"})

    assert report["summary"]["total"] == 2
    assert report["summary"]["failed"] == 0
    assert report["cases"][0]["actual"]["strike_counts"] == [1, 2, 3]
    assert report["cases"][0]["actual"]["persisted_ban"] is True


def test_benchmark_pins_test_settings_instead_of_inheriting_production_env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("GUARDRAILS_ENABLED", "false")
    dataset = load_dataset(DEFAULT_DATASET_PATH)

    report = run_benchmark(dataset, categories={"prompt_injection"})

    assert report["summary"]["total"] == 13
    assert report["summary"]["failed"] == 0


def test_mutation_gate_kills_weakened_abuse_threshold(monkeypatch):
    original = benchmark_module.AbuseTracker.record_violation

    def weakened_record_violation(
        self,
        subjects,
        *,
        violation_code,
        max_strikes,
        strike_window_seconds,
        ban_seconds,
    ):
        return original(
            self,
            subjects,
            violation_code=violation_code,
            max_strikes=max_strikes + 1,
            strike_window_seconds=strike_window_seconds,
            ban_seconds=ban_seconds,
        )

    monkeypatch.setattr(benchmark_module.AbuseTracker, "record_violation", weakened_record_violation)

    report = run_benchmark(load_dataset(DEFAULT_DATASET_PATH), kinds={"abuse"})

    assert {"ABUSE-BAN-001", "ABUSE-BAN-002"} <= _failed_case_ids(report)
    assert any("banned" in failure for case in report["cases"] for failure in case["failures"])


def test_mutation_gate_kills_removed_prompt_injection_patterns(monkeypatch):
    monkeypatch.setattr(input_guard_module, "PROMPT_INJECTION_PATTERNS", ())

    report = run_benchmark(
        load_dataset(DEFAULT_DATASET_PATH),
        categories={"prompt_injection", "context_injection"},
    )

    assert {
        "INPUT-ATTACK-001",
        "INPUT-ATTACK-011",
        "INPUT-ATTACK-017",
        "INPUT-ATTACK-018",
        "INPUT-ATTACK-019",
        "INPUT-ATTACK-023",
        "INPUT-ATTACK-024",
    } <= _failed_case_ids(report)


def test_mutation_gate_kills_disabled_output_sanitization(monkeypatch):
    monkeypatch.setattr(
        OutputGuard,
        "_sanitize_text",
        lambda self, value, *, secret_values: str(value or ""),
    )

    report = run_benchmark(
        load_dataset(DEFAULT_DATASET_PATH),
        categories={"pii_redaction", "secret_redaction", "prompt_leakage"},
    )

    assert {
        "OUTPUT-REDACTION-001",
        "OUTPUT-LEAK-001",
    } <= _failed_case_ids(report)


def test_mutation_gate_kills_untrusted_content_bypass(monkeypatch):
    monkeypatch.setattr(
        UntrustedContentGuard,
        "inspect",
        lambda self, value: GuardrailDecision.allow(sanitized_text=str(value)),
    )

    report = run_benchmark(load_dataset(DEFAULT_DATASET_PATH), categories={"indirect_injection"})

    assert {"UNTRUSTED-CONTENT-001", "UNTRUSTED-CONTENT-002"} <= _failed_case_ids(report)


def test_mutation_gate_kills_confirmation_bypass(monkeypatch):
    monkeypatch.setattr(
        benchmark_module,
        "inspect_tool_calls",
        lambda state, *, allowed_tool_names, settings: GuardrailDecision.allow(),
    )

    report = run_benchmark(load_dataset(DEFAULT_DATASET_PATH), categories={"explicit_confirmation"})

    assert {"TOOL-CONFIRM-001", "TOOL-CONFIRM-008"} <= _failed_case_ids(report)


def test_mutation_gate_kills_conversation_verification_bypass(monkeypatch):
    monkeypatch.setattr(
        benchmark_module.ConversationTokenManager,
        "verify",
        lambda self, token: SimpleNamespace(thread_id="mutant-accepted-thread"),
    )

    report = run_benchmark(load_dataset(DEFAULT_DATASET_PATH), categories={"conversation_binding"})

    assert "CONVERSATION-002" in _failed_case_ids(report)


def test_mutation_gate_kills_rate_limit_bypass(monkeypatch):
    monkeypatch.setattr(
        benchmark_module.SlidingWindowRateLimiter,
        "check",
        lambda self, namespace, subject, *, limit, window_seconds: SimpleNamespace(
            allowed=True,
            retry_after_seconds=None,
        ),
    )

    report = run_benchmark(load_dataset(DEFAULT_DATASET_PATH), categories={"rate_limit"})

    assert {"RATE-LIMIT-001", "RATE-LIMIT-002"} <= _failed_case_ids(report)


def test_benchmark_dataset_validation_rejects_duplicate_ids(tmp_path):
    dataset = deepcopy(load_dataset(DEFAULT_DATASET_PATH))
    dataset["cases"][1]["case_id"] = dataset["cases"][0]["case_id"]
    path = tmp_path / "duplicate.json"
    path.write_text(json.dumps(dataset, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="Duplicate benchmark case_id"):
        load_dataset(path)


def test_benchmark_dataset_validation_rejects_category_coverage_erosion(tmp_path):
    dataset = deepcopy(load_dataset(DEFAULT_DATASET_PATH))
    removed_index = next(index for index, case in enumerate(dataset["cases"]) if case["category"] == "benign_output")
    dataset["cases"].pop(removed_index)
    dataset["case_count"] = len(dataset["cases"])
    path = tmp_path / "coverage-erosion.json"
    path.write_text(json.dumps(dataset, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=r"Category coverage below minimum: benign_output requires 2, found 1",
    ):
        load_dataset(path)


def test_benchmark_dataset_validation_rejects_vacuous_output_expectation(tmp_path):
    dataset = deepcopy(load_dataset(DEFAULT_DATASET_PATH))
    output_case = next(case for case in dataset["cases"] if case["kind"] == "output")
    output_case["expected"] = {}
    path = tmp_path / "vacuous.json"
    path.write_text(json.dumps(dataset, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="require at least one output assertion"):
        load_dataset(path)
