from __future__ import annotations

import statistics
from collections.abc import Mapping, Sequence
from typing import Any


def _mean(values: Sequence[float]) -> float | None:
    return round(statistics.fmean(values), 6) if values else None


def _std(values: Sequence[float]) -> float | None:
    return round(statistics.pstdev(values), 6) if values else None


def _metric_summary(values: Sequence[float]) -> dict[str, float | None]:
    return {
        "mean": _mean(values),
        "stddev": _std(values),
        "min": round(min(values), 6) if values else None,
        "max": round(max(values), 6) if values else None,
    }


def aggregate_stability(
    reports: Sequence[Mapping[str, Any]],
    *,
    selected_case_ids: set[str] | None = None,
) -> dict[str, Any]:
    if len(reports) < 2:
        raise ValueError("Stability evaluation requires at least two independent runs")
    report_cases = [
        {str(case["case_id"]): case for case in report.get("cases", [])}
        for report in reports
    ]
    common_ids = set.intersection(*(set(cases) for cases in report_cases))
    if selected_case_ids:
        common_ids &= selected_case_ids
    active_ids = sorted(
        case_id
        for case_id in common_ids
        if all(cases[case_id].get("evaluation_status") == "active" for cases in report_cases)
    )
    cases: list[dict[str, Any]] = []
    for case_id in active_ids:
        attempts = [cases_by_id[case_id] for cases_by_id in report_cases]
        outcomes = [attempt.get("task_success") for attempt in attempts]
        scored = [value for value in outcomes if isinstance(value, bool)]
        successes = sum(value is True for value in scored)
        latencies = [
            float(attempt["latency_ms"])
            for attempt in attempts
            if isinstance(attempt.get("latency_ms"), (int, float))
        ]
        cases.append(
            {
                "case_id": case_id,
                "runs": len(attempts),
                "scored_runs": len(scored),
                "successes": successes,
                "pass_rate": round(successes / len(scored), 6) if scored else None,
                "pass_at_k_observed": any(value is True for value in scored) if scored else None,
                "pass_all_k": all(value is True for value in scored) if len(scored) == len(attempts) else None,
                "latency_ms": _metric_summary(latencies),
            }
        )

    fully_scored = [case for case in cases if case["scored_runs"] == len(reports)]
    metric_paths = {
        "task_success_rate": ("quality", "task_success_rate"),
        "regression_task_success_rate": ("quality", "regression_task_success_rate"),
        "challenge_task_success_rate": ("quality", "challenge_task_success_rate"),
        "intent_accuracy": ("business_metrics", "intent_accuracy", "rate"),
        "tool_selection_accuracy": ("business_metrics", "tool_selection_accuracy", "rate"),
        "argument_field_f1": ("business_metrics", "argument_accuracy", "mean_field_f1"),
        "slot_precision": (
            "business_metrics",
            "slot_availability_accuracy",
            "precision",
        ),
        "selected_slot_recall": (
            "business_metrics",
            "slot_availability_accuracy",
            "selected_slot_recall",
        ),
        "clean_execution_rate": ("quality", "clean_execution_rate"),
        "hallucination_rate": (
            "business_metrics",
            "hallucination_constraint_violation_rate",
            "hallucination_rate",
        ),
        "constraint_violation_rate": (
            "business_metrics",
            "hallucination_constraint_violation_rate",
            "constraint_violation_rate",
        ),
        "p95_latency_ms": ("business_metrics", "p95_end_to_end_latency", "latency_ms"),
    }
    metric_variance: dict[str, Any] = {}
    for name, path in metric_paths.items():
        values: list[float] = []
        for report in reports:
            value: Any = report
            for key in path:
                value = value.get(key) if isinstance(value, Mapping) else None
            if isinstance(value, (int, float)):
                values.append(float(value))
        metric_variance[name] = {**_metric_summary(values), "observations": len(values)}

    return {
        "schema_version": "1.0",
        "run_count": len(reports),
        "case_count": len(cases),
        "fully_scored_case_count": len(fully_scored),
        "case_pass_at_k_rate": (
            round(sum(case["pass_at_k_observed"] is True for case in fully_scored) / len(fully_scored), 6)
            if fully_scored
            else None
        ),
        "case_pass_all_k_rate": (
            round(sum(case["pass_all_k"] is True for case in fully_scored) / len(fully_scored), 6)
            if fully_scored
            else None
        ),
        "unstable_case_ids": [
            case["case_id"]
            for case in fully_scored
            if case["successes"] not in {0, len(reports)}
        ],
        "metric_variance": metric_variance,
        "cases": cases,
    }


def render_stability_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        "# Độ ổn định benchmark agent",
        "",
        f"- Số lần chạy độc lập: **{report['run_count']}**",
        f"- Case được đo đủ: **{report['fully_scored_case_count']}/{report['case_count']}**",
        f"- Observed pass@k theo case: **{report.get('case_pass_at_k_rate')}**",
        f"- Pass ở mọi lần chạy theo case: **{report.get('case_pass_all_k_rate')}**",
        f"- Case không ổn định: **{', '.join(report.get('unstable_case_ids', [])) or 'Không có'}**",
        "",
        "## Dao động metric giữa các lần chạy",
        "",
        "| Metric | Mean | Stddev | Min | Max |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, values in report.get("metric_variance", {}).items():
        lines.append(
            f"| {name} | {values.get('mean')} | {values.get('stddev')} | "
            f"{values.get('min')} | {values.get('max')} |"
        )
    lines.extend(
        [
            "",
            "## Theo case",
            "",
            "| Case | Pass | Pass rate | Pass@k | Pass mọi lần | Latency mean (ms) |",
            "|---|---:|---:|---|---|---:|",
        ]
    )
    for case in report.get("cases", []):
        lines.append(
            f"| `{case['case_id']}` | {case['successes']}/{case['scored_runs']} | "
            f"{case['pass_rate']} | {case['pass_at_k_observed']} | {case['pass_all_k']} | "
            f"{case['latency_ms']['mean']} |"
        )
    return "\n".join(lines) + "\n"
