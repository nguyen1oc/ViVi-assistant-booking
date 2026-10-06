from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import statistics
import sys
import tempfile
import time
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage

from src.config import Settings
from src.database import Database
from src.guardrails.abuse import AbuseTracker
from src.guardrails.conversation import ConversationTokenManager
from src.guardrails.pipeline import Guardrails
from src.guardrails.rate_limit import SlidingWindowRateLimiter
from src.guardrails.tool_guard import inspect_tool_calls
from src.guardrails.untrusted_content import protect_tool_result_messages

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATASET_PATH = PROJECT_ROOT / "eval" / "benchmarks" / "guardrails_cases.json"
SUPPORTED_KINDS = frozenset({"abuse", "conversation", "input", "output", "rate_limit", "tool", "untrusted_content"})
BENCHMARK_SETTING_DEFAULTS: dict[str, Any] = {
    "app_env": "test",
    "guardrails_enabled": True,
    "guardrails_max_payload_bytes": 16_384,
    "guardrails_max_payload_depth": 6,
    "guardrails_max_payload_nodes": 256,
    "guardrails_max_payload_string_chars": 5_000,
    "guardrails_max_tool_calls_per_message": 3,
    "guardrails_max_output_chars": 8_000,
    "guardrails_abuse_max_strikes": 3,
    "guardrails_abuse_strike_window_seconds": 3_600,
    "guardrails_abuse_ban_seconds": 86_400,
}


@dataclass(frozen=True, slots=True)
class CaseResult:
    case_id: str
    kind: str
    category: str
    passed: bool
    duration_ms: float
    expected: dict[str, Any]
    actual: dict[str, Any]
    failures: list[str]
    tags: list[str]


def load_dataset(path: Path = DEFAULT_DATASET_PATH) -> dict[str, Any]:
    """Load and strictly validate the version-controlled benchmark dataset."""
    try:
        dataset = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Benchmark dataset does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Benchmark dataset is not valid JSON: {exc}") from exc

    if not isinstance(dataset, dict):
        raise ValueError("Benchmark dataset root must be an object")
    if dataset.get("schema_version") != "1.2":
        raise ValueError("Unsupported benchmark schema_version")
    cases = dataset.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Benchmark dataset must contain a non-empty cases list")
    if dataset.get("case_count") != len(cases):
        raise ValueError("case_count does not match the number of cases")

    seen: set[str] = set()
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise ValueError(f"Case at index {index} must be an object")
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError(f"Case at index {index} has an invalid case_id")
        if case_id in seen:
            raise ValueError(f"Duplicate benchmark case_id: {case_id}")
        seen.add(case_id)
        if case.get("kind") not in SUPPORTED_KINDS:
            raise ValueError(f"{case_id}: kind must be one of {sorted(SUPPORTED_KINDS)}")
        if not isinstance(case.get("category"), str) or not case["category"]:
            raise ValueError(f"{case_id}: category must be a non-empty string")
        if not isinstance(case.get("input"), dict):
            raise ValueError(f"{case_id}: input must be an object")
        if not isinstance(case.get("expected"), dict):
            raise ValueError(f"{case_id}: expected must be an object")
        tags = case.get("tags", [])
        if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
            raise ValueError(f"{case_id}: tags must be a string list")
        if case["kind"] in {"input", "tool", "untrusted_content"}:
            if not isinstance(case["expected"].get("allowed"), bool):
                raise ValueError(f"{case_id}: decision cases require expected.allowed")
            if not isinstance(case["expected"].get("code"), str):
                raise ValueError(f"{case_id}: decision cases require expected.code")
        else:
            assertion_names = ("equals", "contains", "not_contains", "ends_with")
            if not any(
                isinstance(case["expected"].get(name), Mapping) and case["expected"][name] for name in assertion_names
            ):
                raise ValueError(f"{case_id}: non-decision cases require at least one output assertion")
    _validate_category_coverage(dataset)
    return dataset


def _validate_category_coverage(dataset: Mapping[str, Any]) -> dict[str, Any]:
    """Fail closed when a benchmark category falls below its declared floor."""
    policy = dataset.get("coverage_policy")
    if not isinstance(policy, Mapping):
        raise ValueError("Benchmark dataset must define coverage_policy")
    raw_minimums = policy.get("minimum_cases_by_category")
    if not isinstance(raw_minimums, Mapping) or not raw_minimums:
        raise ValueError("coverage_policy.minimum_cases_by_category must be a non-empty object")

    minimums: dict[str, int] = {}
    for category, minimum in raw_minimums.items():
        if not isinstance(category, str) or not category:
            raise ValueError("Coverage categories must be non-empty strings")
        if isinstance(minimum, bool) or not isinstance(minimum, int) or minimum < 1:
            raise ValueError(f"Coverage minimum for {category!r} must be a positive integer")
        minimums[category] = minimum

    counts = Counter(str(case["category"]) for case in dataset["cases"])
    undeclared = sorted(set(counts) - set(minimums))
    if undeclared:
        raise ValueError(f"Coverage policy is missing categories: {', '.join(undeclared)}")

    shortfalls = [
        f"{category} requires {minimum}, found {counts.get(category, 0)}"
        for category, minimum in sorted(minimums.items())
        if counts.get(category, 0) < minimum
    ]
    if shortfalls:
        raise ValueError(f"Category coverage below minimum: {'; '.join(shortfalls)}")

    return {
        "passed": True,
        "category_count": len(minimums),
        "minimum_cases_by_category": dict(sorted(minimums.items())),
        "actual_cases_by_category": dict(sorted(counts.items())),
    }


def _settings(case: Mapping[str, Any]) -> Settings:
    overrides = case.get("settings", {})
    if not isinstance(overrides, Mapping):
        raise ValueError(f"{case.get('case_id')}: settings must be an object")
    values = {**BENCHMARK_SETTING_DEFAULTS, **dict(overrides)}
    return Settings(**{"_env_file": None, **values})


def _run_input_case(case: Mapping[str, Any]) -> dict[str, Any]:
    case_input = case["input"]
    guardrails = Guardrails(_settings(case))
    decision = guardrails.inspect_input(
        message=str(case_input.get("message", "Tôi muốn xem thông tin VF8")),
        conversation_id=str(case_input.get("conversation_id", "benchmark-conversation")),
        context=dict(case_input.get("context", {})),
        action=case_input.get("action"),
        action_payload=dict(case_input.get("action_payload", {})),
    )
    return asdict(decision)


def _run_output_case(case: Mapping[str, Any]) -> dict[str, Any]:
    case_input = case["input"]
    guardrails = Guardrails(_settings(case))
    result = case_input.get("result", {})
    if not isinstance(result, dict):
        raise ValueError(f"{case.get('case_id')}: output result must be an object")
    return asdict(guardrails.protect_output(result))


def _run_tool_case(case: Mapping[str, Any]) -> dict[str, Any]:
    case_input = case["input"]
    calls = case_input.get("calls")
    messages: list[AIMessage] = []
    if calls is not None:
        if not isinstance(calls, list):
            raise ValueError(f"{case.get('case_id')}: calls must be a list or null")
        messages = [AIMessage(content="", tool_calls=calls)]
    state: dict[str, Any] = {
        "messages": messages,
        "query": str(case_input.get("query", "Tìm thông tin VF8")),
    }
    if "requested_action" in case_input:
        state["requested_action"] = case_input["requested_action"]
    if "action_payload" in case_input:
        state["action_payload"] = case_input["action_payload"]
    allowed_tool_names = case_input.get("allowed_tool_names", [])
    if not isinstance(allowed_tool_names, list):
        raise ValueError(f"{case.get('case_id')}: allowed_tool_names must be a list")
    decision = inspect_tool_calls(
        state,
        allowed_tool_names=allowed_tool_names,
        settings=_settings(case),
    )
    return asdict(decision)


def _run_untrusted_content_case(case: Mapping[str, Any]) -> dict[str, Any]:
    case_input = case["input"]
    message = ToolMessage(
        content=case_input.get("content", ""),
        tool_call_id=str(case_input.get("tool_call_id", "benchmark-tool-call")),
        name=str(case_input.get("tool_name", "search_knowledge")),
    )
    protected = protect_tool_result_messages([message])[0]
    blocked = isinstance(protected, ToolMessage) and protected.status == "error"
    return {
        "allowed": not blocked,
        "code": "UNTRUSTED_INSTRUCTION_DETECTED" if blocked else "ALLOW",
        "message_type": type(protected).__name__,
        "content": str(protected.content),
        "status": protected.status if isinstance(protected, ToolMessage) else "error",
        "tool_call_id": protected.tool_call_id if isinstance(protected, ToolMessage) else "",
    }


def _run_conversation_case(case: Mapping[str, Any]) -> dict[str, Any]:
    case_input = case["input"]
    operation = case_input.get("operation")
    current = [1_000.0]
    manager = ConversationTokenManager("benchmark-conversation-secret-32b", ttl_seconds=60, now=lambda: current[0])
    identity = manager.issue()
    token = identity.public_token
    if operation == "tamper":
        token = token[:-1] + ("A" if token[-1] != "A" else "B")
    elif operation == "expire":
        current[0] = 1_061.0
    elif operation != "round_trip":
        raise ValueError(f"{case.get('case_id')}: unsupported conversation operation")
    verified = manager.verify(token)
    return {
        "valid": verified is not None,
        "thread_matches": verified is not None and verified.thread_id == identity.thread_id,
    }


def _run_rate_limit_case(case: Mapping[str, Any]) -> dict[str, Any]:
    case_input = case["input"]
    current = [100.0]
    limiter = SlidingWindowRateLimiter(now=lambda: current[0])
    limit = int(case_input.get("limit", 2))
    attempts = int(case_input.get("attempts", 3))
    decisions = [limiter.check("benchmark", "same-subject", limit=limit, window_seconds=60) for _ in range(attempts)]
    current[0] = 161.0
    recovered = limiter.check("benchmark", "same-subject", limit=limit, window_seconds=60)
    return {
        "allowed": [decision.allowed for decision in decisions],
        "retry_after_seconds": decisions[-1].retry_after_seconds,
        "recovered": recovered.allowed,
    }


def _run_abuse_case(case: Mapping[str, Any]) -> dict[str, Any]:
    case_input = case["input"]
    if case_input.get("operation") != "three_strikes":
        raise ValueError(f"{case.get('case_id')}: unsupported abuse operation")
    settings = _settings(case)
    current = datetime(2026, 8, 21, 8, 0, tzinfo=UTC)
    subjects = ("session:benchmark-client", "thread:benchmark-conversation")
    violation_codes = case_input.get(
        "violation_codes",
        ["PROMPT_INJECTION_OVERRIDE", "ABUSIVE_LANGUAGE", "ROLE_INJECTION"],
    )
    if not isinstance(violation_codes, list) or not all(isinstance(code, str) for code in violation_codes):
        raise ValueError(f"{case.get('case_id')}: violation_codes must be a string list")
    with tempfile.TemporaryDirectory(prefix="guardrail-abuse-benchmark-") as temp_dir:
        database = Database(Path(temp_dir) / "abuse.db")
        tracker = AbuseTracker(database, now=lambda: current)
        tracker.ensure_schema()
        statuses = [
            tracker.record_violation(
                subjects,
                violation_code=code,
                max_strikes=settings.guardrails_abuse_max_strikes,
                strike_window_seconds=settings.guardrails_abuse_strike_window_seconds,
                ban_seconds=settings.guardrails_abuse_ban_seconds,
            )
            for code in violation_codes
        ]
        persisted = AbuseTracker(database, now=lambda: current).check(subjects)
        with database.connect() as connection:
            stored_subject_rows = connection.execute("SELECT count(*) FROM guardrail_abuse_subjects").fetchone()[0]
    return {
        "strike_counts": [status.strike_count for status in statuses],
        "banned": [status.banned for status in statuses],
        "persisted_ban": persisted.banned,
        "retry_after_seconds": persisted.retry_after_seconds,
        "stored_subject_rows": stored_subject_rows,
    }


def _read_path(value: Any, path: str) -> Any:
    current = value
    for segment in path.split("."):
        if isinstance(current, Mapping):
            if segment not in current:
                raise KeyError(path)
            current = current[segment]
        elif isinstance(current, Sequence) and not isinstance(current, (str, bytes, bytearray)):
            current = current[int(segment)]
        else:
            raise KeyError(path)
    return current


def _evaluate_expected(actual: Mapping[str, Any], expected: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    for field in ("allowed", "code"):
        if field in expected and actual.get(field) != expected[field]:
            failures.append(f"{field}: expected {expected[field]!r}, got {actual.get(field)!r}")

    for path, expected_value in expected.get("equals", {}).items():
        try:
            actual_value = _read_path(actual, path)
        except (KeyError, IndexError, ValueError):
            failures.append(f"{path}: field is missing")
            continue
        if actual_value != expected_value:
            failures.append(f"{path}: expected {expected_value!r}, got {actual_value!r}")

    for operation in ("contains", "not_contains", "ends_with"):
        for path, expectation in expected.get(operation, {}).items():
            try:
                actual_value = str(_read_path(actual, path))
            except (KeyError, IndexError, ValueError):
                failures.append(f"{path}: field is missing")
                continue
            values = expectation if isinstance(expectation, list) else [expectation]
            for item in map(str, values):
                if operation == "contains" and item not in actual_value:
                    failures.append(f"{path}: expected to contain {item!r}")
                elif operation == "not_contains" and item in actual_value:
                    failures.append(f"{path}: must not contain {item!r}")
                elif operation == "ends_with" and not actual_value.endswith(item):
                    failures.append(f"{path}: expected to end with {item!r}")
    return failures


def run_case(case: Mapping[str, Any]) -> CaseResult:
    started = time.perf_counter_ns()
    failures: list[str] = []
    actual: dict[str, Any]
    try:
        kind = str(case["kind"])
        if kind == "input":
            actual = _run_input_case(case)
        elif kind == "output":
            actual = _run_output_case(case)
        elif kind == "tool":
            actual = _run_tool_case(case)
        elif kind == "untrusted_content":
            actual = _run_untrusted_content_case(case)
        elif kind == "conversation":
            actual = _run_conversation_case(case)
        elif kind == "rate_limit":
            actual = _run_rate_limit_case(case)
        elif kind == "abuse":
            actual = _run_abuse_case(case)
        else:  # load_dataset prevents this; retain a fail-closed runtime guard.
            raise ValueError(f"Unsupported case kind: {kind}")
        failures.extend(_evaluate_expected(actual, case["expected"]))
    except Exception as exc:
        actual = {"exception": f"{type(exc).__name__}: {exc}"}
        failures.append(actual["exception"])
    duration_ms = (time.perf_counter_ns() - started) / 1_000_000
    return CaseResult(
        case_id=str(case["case_id"]),
        kind=str(case["kind"]),
        category=str(case["category"]),
        passed=not failures,
        duration_ms=round(duration_ms, 4),
        expected=dict(case["expected"]),
        actual=actual,
        failures=failures,
        tags=list(case.get("tags", [])),
    )


def _rate(passed: int, total: int) -> float | None:
    return round(passed / total, 6) if total else None


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return round(ordered[index], 4)


def _group_summary(results: list[CaseResult], attribute: str) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[CaseResult]] = defaultdict(list)
    for result in results:
        grouped[str(getattr(result, attribute))].append(result)
    return {
        key: {
            "total": len(items),
            "passed": sum(item.passed for item in items),
            "failed": sum(not item.passed for item in items),
            "pass_rate": _rate(sum(item.passed for item in items), len(items)),
        }
        for key, items in sorted(grouped.items())
    }


def run_benchmark(
    dataset: Mapping[str, Any],
    *,
    kinds: set[str] | None = None,
    categories: set[str] | None = None,
    tags: set[str] | None = None,
) -> dict[str, Any]:
    """Execute selected deterministic cases and return a machine-readable report."""
    coverage_gate = _validate_category_coverage(dataset)
    selected: list[dict[str, Any]] = []
    for case in dataset["cases"]:
        if kinds and case["kind"] not in kinds:
            continue
        if categories and case["category"] not in categories:
            continue
        case_tags = set(case.get("tags", []))
        if tags and not tags.issubset(case_tags):
            continue
        selected.append(case)
    if not selected:
        raise ValueError("No benchmark cases matched the requested filters")

    started = time.perf_counter()
    results = [run_case(case) for case in selected]
    elapsed_ms = round((time.perf_counter() - started) * 1000, 4)
    passed = sum(result.passed for result in results)
    decision_kinds = {"input", "tool", "untrusted_content"}
    attack_results = [
        result for result in results if result.kind in decision_kinds and result.expected.get("allowed") is False
    ]
    benign_results = [
        result for result in results if result.kind in decision_kinds and result.expected.get("allowed") is True
    ]
    output_results = [result for result in results if result.kind == "output"]
    durations = [result.duration_ms for result in results]
    dataset_bytes = json.dumps(dataset, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()

    return {
        "schema_version": "1.0",
        "benchmark_name": dataset.get("benchmark_name", "guardrails"),
        "dataset_schema_version": dataset.get("schema_version"),
        "dataset_sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "generated_at": datetime.now(UTC).isoformat(),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "filters": {
            "kinds": sorted(kinds or []),
            "categories": sorted(categories or []),
            "tags": sorted(tags or []),
        },
        "coverage_gate": coverage_gate,
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "pass_rate": _rate(passed, len(results)),
            "elapsed_ms": elapsed_ms,
        },
        "quality_metrics": {
            "attack_block_accuracy": _rate(sum(item.passed for item in attack_results), len(attack_results)),
            "benign_allow_accuracy": _rate(sum(item.passed for item in benign_results), len(benign_results)),
            "output_protection_accuracy": _rate(sum(item.passed for item in output_results), len(output_results)),
            "latency_median_ms": round(statistics.median(durations), 4),
            "latency_p95_ms": _percentile(durations, 0.95),
        },
        "case_distribution": dict(sorted(Counter(result.kind for result in results).items())),
        "by_kind": _group_summary(results, "kind"),
        "by_category": _group_summary(results, "category"),
        "cases": [asdict(result) for result in results],
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    summary = report["summary"]
    metrics = report["quality_metrics"]
    lines = [
        "# Guardrail Benchmark Report",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Dataset SHA-256: `{report['dataset_sha256']}`",
        f"- Result: **{summary['passed']}/{summary['total']} PASS** ({summary['pass_rate']:.2%})",
        f"- Runtime: `{summary['elapsed_ms']:.4f} ms`",
        f"- Category coverage gate: **{'PASS' if report['coverage_gate']['passed'] else 'FAIL'}** "
        f"({report['coverage_gate']['category_count']} categories)",
        "",
        "## Quality Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    for label, key in (
        ("Attack-block accuracy", "attack_block_accuracy"),
        ("Benign-allow accuracy", "benign_allow_accuracy"),
        ("Output-protection accuracy", "output_protection_accuracy"),
    ):
        value = metrics[key]
        lines.append(f"| {label} | {'N/A' if value is None else f'{value:.2%}'} |")
    lines.extend(
        [
            f"| Median latency | {metrics['latency_median_ms']:.4f} ms |",
            f"| p95 latency | {metrics['latency_p95_ms']:.4f} ms |",
            "",
            "## Results By Category",
            "",
            "| Category | Passed | Total | Pass rate |",
            "|---|---:|---:|---:|",
        ]
    )
    for category, category_summary in report["by_category"].items():
        lines.append(
            f"| `{category}` | {category_summary['passed']} | {category_summary['total']} | "
            f"{category_summary['pass_rate']:.2%} |"
        )
    failures = [case for case in report["cases"] if not case["passed"]]
    lines.extend(["", "## Failures", ""])
    if not failures:
        lines.append("No failed cases.")
    else:
        for case in failures:
            lines.append(f"### `{case['case_id']}`")
            lines.append("")
            lines.extend(f"- {failure}" for failure in case["failures"])
            lines.append("")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This is a deterministic, offline policy benchmark. A pass demonstrates regression stability for the "
            "curated cases; it does not prove that every prompt injection or data-leak technique is covered. "
            "Authorization, rate limiting, domain validation and live-agent behavioral evaluation remain separate gates.",
            "",
        ]
    )
    return "\n".join(lines)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def verify_baseline(report: Mapping[str, Any], path: Path) -> list[str]:
    """Return stable baseline mismatches while ignoring runtime-only fields."""
    try:
        baseline = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [f"baseline does not exist: {path}"]
    except json.JSONDecodeError as exc:
        return [f"baseline is not valid JSON: {exc}"]
    if not isinstance(baseline, Mapping):
        return ["baseline root must be an object"]

    failures: list[str] = []
    for field in ("benchmark_name", "dataset_schema_version", "dataset_sha256"):
        if baseline.get(field) != report.get(field):
            failures.append(f"{field} does not match the current benchmark")

    baseline_summary = baseline.get("summary")
    report_summary = report.get("summary")
    if not isinstance(baseline_summary, Mapping) or not isinstance(report_summary, Mapping):
        failures.append("baseline and current report must contain summary objects")
    else:
        if baseline_summary.get("total") != report_summary.get("total"):
            failures.append("baseline case total does not match the current benchmark")
        if baseline_summary.get("failed") != 0 or baseline_summary.get("pass_rate") != 1.0:
            failures.append("baseline must record a 100% passing run")

    baseline_case_ids = {
        str(case.get("case_id"))
        for case in baseline.get("cases", [])
        if isinstance(case, Mapping) and case.get("case_id")
    }
    report_case_ids = {
        str(case.get("case_id"))
        for case in report.get("cases", [])
        if isinstance(case, Mapping) and case.get("case_id")
    }
    if baseline_case_ids != report_case_ids:
        failures.append("baseline case IDs do not match the current benchmark")

    baseline_coverage = baseline.get("coverage_gate")
    if not isinstance(baseline_coverage, Mapping) or baseline_coverage.get("passed") is not True:
        failures.append("baseline must contain a passing category coverage gate")
    return failures


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the deterministic VinFast guardrail benchmark.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--kind", action="append", choices=sorted(SUPPORTED_KINDS))
    parser.add_argument("--category", action="append")
    parser.add_argument("--tag", action="append")
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument("--verify-baseline", type=Path)
    parser.add_argument("--fail-under", type=float, default=1.0)
    parser.add_argument("--max-p95-ms", type=float)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not 0 <= args.fail_under <= 1:
        raise SystemExit("--fail-under must be between 0 and 1")
    dataset = load_dataset(args.dataset)
    report = run_benchmark(
        dataset,
        kinds=set(args.kind or []),
        categories=set(args.category or []),
        tags=set(args.tag or []),
    )
    markdown = render_markdown(report)
    if args.json_output:
        _write(args.json_output, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    if args.markdown_output:
        _write(args.markdown_output, markdown)
    baseline_failures = verify_baseline(report, args.verify_baseline) if args.verify_baseline else []
    for failure in baseline_failures:
        print(f"baseline: {failure}", file=sys.stderr)
    print(
        f"guardrails: {report['summary']['passed']}/{report['summary']['total']} passed "
        f"({report['summary']['pass_rate']:.2%}); p95={report['quality_metrics']['latency_p95_ms']:.4f}ms"
    )
    failed = report["summary"]["pass_rate"] < args.fail_under or bool(baseline_failures)
    if args.max_p95_ms is not None:
        failed = failed or report["quality_metrics"]["latency_p95_ms"] > args.max_p95_ms
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
