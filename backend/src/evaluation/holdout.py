"""One-shot hidden holdout validation, sealing, and public reporting."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REQUIRED_MUTATION_CATEGORIES = (
    "expression",
    "typo",
    "time",
    "showroom",
    "multi_turn",
    "tool_failure",
)
REQUIRED_HUMAN_FIELDS = (
    "task_success",
    "correctness_1_5",
    "relevance_1_5",
    "groundedness_1_5",
    "safety_1_5",
    "satisfaction_1_5",
)


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalized_prompt(case: Mapping[str, Any]) -> str:
    parts = [
        str(turn.get("content") or "").casefold().strip()
        for turn in case.get("turns", [])
        if isinstance(turn, Mapping) and turn.get("role") in {"user", "action"}
    ]
    return "\n".join(" ".join(part.split()) for part in parts)


def validate_hidden_holdout(
    dataset: Mapping[str, Any],
    regression_dataset: Mapping[str, Any],
    *,
    expected_regression_count: int = 57,
) -> dict[str, int]:
    """Validate split isolation and return mutation-category counts."""
    regression_cases = regression_dataset.get("cases")
    holdout_cases = dataset.get("cases")
    if not isinstance(regression_cases, list) or regression_dataset.get("case_count") != len(regression_cases):
        raise ValueError("Regression dataset case_count does not match its cases array")
    if len(regression_cases) != expected_regression_count:
        raise ValueError(
            f"Regression suite must remain exactly {expected_regression_count} cases; found {len(regression_cases)}"
        )
    if not isinstance(holdout_cases, list) or dataset.get("case_count") != len(holdout_cases):
        raise ValueError("Hidden holdout case_count does not match its cases array")
    if dataset.get("split") != "hidden_holdout":
        raise ValueError("Hidden holdout dataset must declare split='hidden_holdout'")
    if not holdout_cases:
        raise ValueError("Hidden holdout dataset is empty")

    regression_ids = {str(case.get("case_id") or "") for case in regression_cases}
    regression_prompts = {_normalized_prompt(case) for case in regression_cases}
    holdout_ids: set[str] = set()
    category_counts: Counter[str] = Counter()
    for case in holdout_cases:
        if not isinstance(case, Mapping):
            raise ValueError("Every hidden holdout case must be an object")
        case_id = str(case.get("case_id") or "")
        if not case_id or case_id in holdout_ids:
            raise ValueError(f"Hidden holdout case IDs must be present and unique: {case_id!r}")
        if case_id in regression_ids:
            raise ValueError(f"Hidden holdout case overlaps regression suite: {case_id}")
        holdout_ids.add(case_id)
        if case.get("evaluation_status") != "active":
            raise ValueError(f"Hidden holdout case must be active: {case_id}")
        if case.get("review_status") != "FROZEN_HOLDOUT_NOT_HUMAN_REVIEWED":
            raise ValueError(f"Hidden holdout case has invalid review_status: {case_id}")
        tags = {str(tag) for tag in case.get("tags", [])}
        if "hidden_holdout" not in tags:
            raise ValueError(f"Hidden holdout tag is missing: {case_id}")
        category = str(case.get("mutation_category") or "")
        if category not in REQUIRED_MUTATION_CATEGORIES:
            raise ValueError(f"Hidden holdout case has an unsupported mutation_category: {case_id}")
        category_counts[category] += 1
        sources = {str(source) for source in case.get("source_case_ids", [])}
        if not sources or not sources <= regression_ids:
            raise ValueError(f"Hidden holdout sources must reference regression case IDs: {case_id}")
        prompt = _normalized_prompt(case)
        if not prompt or prompt in regression_prompts:
            raise ValueError(f"Hidden holdout prompt must differ from every regression prompt: {case_id}")
        expected = case.get("expected")
        if not isinstance(expected, Mapping) or "intent" not in expected or "tool" not in expected:
            raise ValueError(f"Hidden holdout expected contract is incomplete: {case_id}")

    missing = [category for category in REQUIRED_MUTATION_CATEGORIES if category_counts[category] == 0]
    if missing:
        raise ValueError(f"Hidden holdout is missing mutation categories: {', '.join(missing)}")
    declared_counts = dataset.get("mutation_category_counts")
    actual_counts = {category: category_counts[category] for category in REQUIRED_MUTATION_CATEGORIES}
    if declared_counts != actual_counts:
        raise ValueError("Hidden holdout mutation_category_counts does not match the cases array")
    return actual_counts


def application_fingerprint(project_root: Path) -> str:
    """Hash executable agent code and dependency/config contracts in a stable order."""
    candidates = [
        *sorted((project_root / "backend" / "src").rglob("*.py")),
        project_root / "backend" / "requirements.txt",
        project_root / ".env.example",
    ]
    digest = hashlib.sha256()
    for path in candidates:
        if not path.is_file():
            continue
        digest.update(path.relative_to(project_root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def git_metadata(project_root: Path) -> dict[str, Any]:
    def run(*arguments: str) -> str | None:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=project_root,
            capture_output=True,
            check=False,
            text=True,
        )
        return completed.stdout.strip() if completed.returncode == 0 else None

    status = run("status", "--porcelain=v1", "--untracked-files=all")
    return {
        "commit": run("rev-parse", "HEAD"),
        "dirty": bool(status),
        "worktree_status_sha256": hashlib.sha256((status or "").encode("utf-8")).hexdigest(),
    }


def claim_one_shot_lock(path: Path, payload: Mapping[str, Any]) -> None:
    """Atomically consume the one permitted live attempt."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(dict(payload), handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def update_lock(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def verify_frozen_artifacts(lock: Mapping[str, Any], project_root: Path) -> list[str]:
    errors: list[str] = []
    artifacts = dict(lock.get("artifacts", {}))
    artifacts.update(
        {str(label): item for label, item in lock.get("reporting_artifacts", {}).items() if isinstance(item, Mapping)}
    )
    for label, item in artifacts.items():
        if not isinstance(item, Mapping):
            errors.append(f"{label}: invalid artifact metadata")
            continue
        relative = str(item.get("path") or "")
        expected = str(item.get("sha256") or "")
        path = project_root / relative
        if not path.is_file():
            errors.append(f"{label}: missing {relative}")
        elif sha256_file(path) != expected:
            errors.append(f"{label}: checksum mismatch")
    return errors


def _completed_human_review_counts(ratings_path: Path | None) -> Counter[str]:
    if ratings_path is None or not ratings_path.is_file():
        return Counter()
    with ratings_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    completed_pairs: set[tuple[str, str]] = set()
    for row in rows:
        case_id = str(row.get("case_id") or "").strip()
        reviewer_id = str(row.get("reviewer_id") or "").strip()
        if case_id and reviewer_id and all(str(row.get(field) or "").strip() for field in REQUIRED_HUMAN_FIELDS):
            completed_pairs.add((case_id, reviewer_id))
    return Counter(case_id for case_id, _ in completed_pairs)


def human_review_gate(
    regression_ids: Sequence[str],
    holdout_ids: Sequence[str],
    ratings_paths: Sequence[Path],
    *,
    minimum_reviews_per_case: int = 2,
) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    for path in ratings_paths:
        counts.update(_completed_human_review_counts(path))

    def split(ids: Sequence[str]) -> dict[str, Any]:
        unique_ids = set(ids)
        covered = sum(counts[case_id] >= minimum_reviews_per_case for case_id in unique_ids)
        return {
            "case_count": len(unique_ids),
            "cases_with_minimum_reviews": covered,
            "coverage_rate": round(covered / len(unique_ids), 4) if unique_ids else None,
        }

    regression = split(regression_ids)
    holdout = split(holdout_ids)
    combined = split([*regression_ids, *holdout_ids])
    sufficient = combined["case_count"] > 0 and combined["cases_with_minimum_reviews"] == combined["case_count"]
    return {
        "status": "COMPLETE" if sufficient else "PARTIAL",
        "minimum_reviews_per_case": minimum_reviews_per_case,
        "required_coverage_rate": 1.0,
        "regression": regression,
        "hidden_holdout": holdout,
        "combined": combined,
        "sufficient_for_overall": sufficient,
    }


def _task_split(report: Mapping[str, Any]) -> dict[str, Any]:
    quality = report.get("quality", {})
    case_scores = [case for case in report.get("cases", []) if isinstance(case, Mapping)]
    passed = sum(case.get("task_success") is True for case in case_scores)
    failed = sum(case.get("task_success") is False for case in case_scores)
    scored = int(quality.get("task_success_scored_cases") or 0)
    return {
        "status": report.get("run", {}).get("status"),
        "task_success_rate": quality.get("task_success_rate"),
        "passed_cases": passed,
        "failed_cases": failed,
        "scored_cases": scored,
        "total_cases": report.get("dataset", {}).get("active_cases"),
        "wilson_95": quality.get("task_success_confidence_interval_95"),
        "intent_accuracy": quality.get("intent_accuracy"),
        "tool_accuracy": quality.get("tool_accuracy"),
        "argument_field_f1": quality.get("argument_mean_field_f1"),
        "latency_p95_ms": report.get("performance", {}).get("latency_p95_ms"),
    }


def build_public_summary(
    *,
    regression_dataset: Mapping[str, Any],
    regression_report: Mapping[str, Any],
    holdout_dataset: Mapping[str, Any],
    holdout_report: Mapping[str, Any],
    ratings_paths: Sequence[Path],
    freeze: Mapping[str, Any],
) -> dict[str, Any]:
    regression_ids = [str(case["case_id"]) for case in regression_dataset["cases"]]
    holdout_ids = [str(case["case_id"]) for case in holdout_dataset["cases"]]
    gate = human_review_gate(regression_ids, holdout_ids, ratings_paths)
    regression_split = _task_split(regression_report)
    holdout_split = _task_split(holdout_report)

    scores_by_id = {
        str(case.get("case_id")): case for case in holdout_report.get("cases", []) if isinstance(case, Mapping)
    }
    by_category: dict[str, dict[str, Any]] = {}
    grouped: defaultdict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for case in holdout_dataset["cases"]:
        score = scores_by_id.get(str(case["case_id"]))
        if score is not None:
            grouped[str(case["mutation_category"])].append(score)
    for category in REQUIRED_MUTATION_CATEGORIES:
        scores = grouped[category]
        scored = sum(score.get("task_success") is not None for score in scores)
        passed = sum(score.get("task_success") is True for score in scores)
        by_category[category] = {
            "passed_cases": passed,
            "scored_cases": scored,
            "total_cases": sum(case.get("mutation_category") == category for case in holdout_dataset.get("cases", [])),
            "task_success_rate": round(passed / scored, 4) if scored else None,
        }

    automated_passed = regression_split["passed_cases"] + holdout_split["passed_cases"]
    automated_scored = regression_split["scored_cases"] + holdout_split["scored_cases"]
    publish_overall = gate["sufficient_for_overall"]
    overall_rate = round(automated_passed / automated_scored, 4) if automated_scored and publish_overall else None
    return {
        "schema_version": "1.0",
        "generated_at": now_iso(),
        "policy": {
            "regression_suite_fixed_cases": len(regression_ids),
            "holdout_one_shot": True,
            "failed_cases_replaced_or_rerun": False,
            "overall_requires_full_two_reviewer_coverage": True,
        },
        "freeze": dict(freeze),
        "splits": {
            "regression": regression_split,
            "hidden_holdout": holdout_split,
        },
        "hidden_holdout_by_mutation_category": by_category,
        "human_review_gate": gate,
        "overall": {
            "status": "PUBLISHED" if publish_overall else "WITHHELD_HUMAN_REVIEW_INSUFFICIENT",
            "task_success_rate": overall_rate if publish_overall else None,
            "passed_cases": automated_passed if publish_overall else None,
            "scored_cases": automated_scored if publish_overall else None,
            "note": (
                "Overall is published because every regression and holdout case has two completed human reviews."
                if publish_overall
                else "Overall is intentionally withheld until every regression and holdout case has two completed human reviews."
            ),
        },
    }


def _percent(value: Any) -> str:
    return "NOT_RUN" if value is None else f"{float(value) * 100:.2f}%"


def render_public_summary(summary: Mapping[str, Any]) -> str:
    regression = summary["splits"]["regression"]
    holdout = summary["splits"]["hidden_holdout"]
    gate = summary["human_review_gate"]
    overall = summary["overall"]
    lines = [
        "# Benchmark regression và hidden holdout",
        "",
        "Kết quả dưới đây tách riêng bộ regression đã biết và hidden holdout chạy one-shot. "
        "Không thay case fail, không rerun để chọn kết quả đẹp hơn.",
        "",
        "## Kết quả theo split",
        "",
        "| Split | Task success | Số case | P95 latency |",
        "|---|---:|---:|---:|",
        f"| Regression | **{_percent(regression['task_success_rate'])}** | "
        f"{regression['passed_cases']}/{regression['scored_cases']} | {regression['latency_p95_ms']} ms |",
        f"| Hidden holdout | **{_percent(holdout['task_success_rate'])}** | "
        f"{holdout['passed_cases']}/{holdout['scored_cases']} | {holdout['latency_p95_ms']} ms |",
        "",
        "## Hidden holdout theo mutation",
        "",
        "| Mutation | Task success | Số case |",
        "|---|---:|---:|",
    ]
    for category in REQUIRED_MUTATION_CATEGORIES:
        item = summary["hidden_holdout_by_mutation_category"][category]
        lines.append(
            f"| `{category}` | {_percent(item['task_success_rate'])} | {item['passed_cases']}/{item['scored_cases']} |"
        )
    combined = gate["combined"]
    lines.extend(
        [
            "",
            "## Human-review gate và overall",
            "",
            f"- Gate: **{gate['status']}**; yêu cầu 2 review hoàn chỉnh cho mỗi case và coverage 100%.",
            f"- Coverage đạt chuẩn: **{combined['cases_with_minimum_reviews']}/{combined['case_count']} case** "
            f"({_percent(combined['coverage_rate'])}).",
            f"- Overall: **{overall['status']}**.",
            "- Khi gate chưa đạt, không có điểm gộp nào được tính hoặc lưu trong artifact công khai.",
            "",
            "## Bằng chứng đóng băng",
            "",
            f"- Trạng thái lần chạy: **{summary['freeze'].get('status')}**.",
            f"- Số attempt live: **{summary['freeze'].get('attempt_count')}**.",
            f"- Dataset SHA-256: `{summary['freeze'].get('dataset_sha256')}`.",
            f"- Application SHA-256: `{summary['freeze'].get('application_sha256')}`.",
            "- Dataset và raw trace nằm trong thư mục private bị Git bỏ qua; manifest công khai không chứa prompt/label.",
            "",
        ]
    )
    return "\n".join(lines)
