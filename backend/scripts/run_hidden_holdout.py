"""Validate or consume the single permitted hidden-holdout live attempt."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import traceback
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.evaluation.agent_benchmark import (  # noqa: E402
    _redact,
    load_golden_dataset,
    run_live_predictions,
    score_evaluation,
)
from src.evaluation.holdout import (  # noqa: E402
    application_fingerprint,
    build_public_summary,
    claim_one_shot_lock,
    git_metadata,
    now_iso,
    render_public_summary,
    sha256_file,
    update_lock,
    validate_hidden_holdout,
    verify_frozen_artifacts,
)

DEFAULT_DATASET = PROJECT_ROOT / "eval" / "holdout" / "private" / "hidden_cases.json"
DEFAULT_LOCK = PROJECT_ROOT / "eval" / "holdout" / "frozen-manifest.json"
DEFAULT_PRIVATE_PREDICTIONS = PROJECT_ROOT / "eval" / "holdout" / "private" / "frozen-predictions.json"
DEFAULT_PRIVATE_REPORT = PROJECT_ROOT / "eval" / "holdout" / "private" / "frozen-evaluation.json"
DEFAULT_PUBLIC_JSON = PROJECT_ROOT / "eval" / "results" / "benchmark-splits.json"
DEFAULT_PUBLIC_MARKDOWN = PROJECT_ROOT / "eval" / "results" / "benchmark-splits.md"
DEFAULT_REGRESSION = PROJECT_ROOT / "eval" / "golden" / "agent_cases.json"
DEFAULT_REGRESSION_REPORT = PROJECT_ROOT / "eval" / "results" / "agent-evaluation.json"
DEFAULT_REGRESSION_RATINGS = PROJECT_ROOT / "eval" / "human" / "reviews.csv"
DEFAULT_HOLDOUT_RATINGS = PROJECT_ROOT / "eval" / "holdout" / "private" / "reviews.csv"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return payload


def _relative(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="One-shot hidden holdout runner")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate-only", action="store_true", help="Validate without consuming the live attempt")
    mode.add_argument("--execute-once", action="store_true", help="Consume the only allowed live attempt")
    mode.add_argument("--verify-freeze", action="store_true", help="Verify frozen artifact checksums")
    mode.add_argument(
        "--refresh-public-report",
        action="store_true",
        help="Recompute only the public human-review gate from already frozen artifacts",
    )
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--regression", type=Path, default=DEFAULT_REGRESSION)
    parser.add_argument("--regression-report", type=Path, default=DEFAULT_REGRESSION_REPORT)
    parser.add_argument("--regression-ratings", type=Path, default=DEFAULT_REGRESSION_RATINGS)
    parser.add_argument("--holdout-ratings", type=Path, default=DEFAULT_HOLDOUT_RATINGS)
    parser.add_argument("--private-predictions", type=Path, default=DEFAULT_PRIVATE_PREDICTIONS)
    parser.add_argument("--private-report", type=Path, default=DEFAULT_PRIVATE_REPORT)
    parser.add_argument("--public-json", type=Path, default=DEFAULT_PUBLIC_JSON)
    parser.add_argument("--public-markdown", type=Path, default=DEFAULT_PUBLIC_MARKDOWN)
    parser.add_argument("--eval-data-dir", type=Path)
    return parser


async def _main(args: argparse.Namespace) -> int:
    if args.verify_freeze:
        if not args.lock.is_file():
            raise SystemExit(f"Freeze manifest does not exist: {args.lock}")
        errors = verify_frozen_artifacts(_read_json(args.lock), PROJECT_ROOT)
        if errors:
            raise SystemExit("Frozen artifact verification failed:\n- " + "\n- ".join(errors))
        print(f"Frozen artifacts verified: {args.lock}")
        return 0

    dataset = _read_json(args.dataset)
    regression = load_golden_dataset(args.regression)
    category_counts = validate_hidden_holdout(dataset, regression)
    print(
        f"Validated hidden holdout: {dataset['case_count']} cases; "
        + ", ".join(f"{key}={value}" for key, value in category_counts.items())
    )
    if args.validate_only:
        return 0
    if args.refresh_public_report:
        if not args.lock.is_file():
            raise SystemExit(f"Freeze manifest does not exist: {args.lock}")
        freeze = _read_json(args.lock)
        if freeze.get("status") != "COMPLETED" or freeze.get("attempt_count") != 1:
            raise SystemExit("A completed one-shot freeze is required before refreshing the public report")
        errors = verify_frozen_artifacts(freeze, PROJECT_ROOT)
        if errors:
            raise SystemExit("Frozen artifact verification failed:\n- " + "\n- ".join(errors))
        report = _read_json(args.private_report)
        regression_report = _read_json(args.regression_report)
        public_freeze = {
            key: freeze.get(key)
            for key in (
                "schema_version",
                "status",
                "attempt_count",
                "started_at",
                "completed_at",
                "dataset_sha256",
                "regression_sha256",
                "application_sha256",
                "git",
                "policy",
                "model",
            )
        }
        summary = build_public_summary(
            regression_dataset=regression,
            regression_report=regression_report,
            holdout_dataset=dataset,
            holdout_report=report,
            ratings_paths=[args.regression_ratings, args.holdout_ratings],
            freeze=public_freeze,
        )
        _write_json(args.public_json, summary)
        args.public_markdown.parent.mkdir(parents=True, exist_ok=True)
        args.public_markdown.write_text(render_public_summary(summary), encoding="utf-8")
        for label in ("public_summary_json", "public_summary_markdown"):
            freeze.get("artifacts", {}).pop(label, None)
        freeze["reporting_artifacts"] = {
            "refreshed_at": now_iso(),
            "public_summary_json": {
                "path": _relative(args.public_json),
                "sha256": sha256_file(args.public_json),
            },
            "public_summary_markdown": {
                "path": _relative(args.public_markdown),
                "sha256": sha256_file(args.public_markdown),
            },
        }
        update_lock(args.lock, freeze)
        print(render_public_summary(summary))
        return 0
    if args.lock.exists():
        raise SystemExit(
            f"One-shot attempt already consumed; rerun is forbidden. Verify with --verify-freeze: {args.lock}"
        )

    freeze: dict[str, Any] = {
        "schema_version": "1.0",
        "status": "RUNNING",
        "attempt_count": 1,
        "started_at": now_iso(),
        "dataset_sha256": sha256_file(args.dataset),
        "regression_sha256": sha256_file(args.regression),
        "application_sha256": application_fingerprint(PROJECT_ROOT),
        "git": git_metadata(PROJECT_ROOT),
        "policy": {
            "one_shot": True,
            "rerun_allowed": False,
            "replace_failed_cases_allowed": False,
            "code_tuning_from_holdout_allowed": False,
        },
        "artifacts": {},
    }
    claim_one_shot_lock(args.lock, freeze)
    try:
        predictions = await run_live_predictions(
            dataset,
            eval_data_dir=args.eval_data_dir,
            llm_judge=False,
        )
        redacted_predictions = _redact(predictions)
        _write_json(args.private_predictions, redacted_predictions)
        report = score_evaluation(
            dataset,
            redacted_predictions,
            dataset_path=args.dataset,
            negative_dataset={"cases": []},
        )
        _write_json(args.private_report, _redact(report))

        freeze.update(
            {
                "status": "COMPLETED",
                "completed_at": now_iso(),
                "model": predictions.get("model"),
                "artifacts": {
                    "dataset": {"path": _relative(args.dataset), "sha256": sha256_file(args.dataset)},
                    "predictions": {
                        "path": _relative(args.private_predictions),
                        "sha256": sha256_file(args.private_predictions),
                    },
                    "evaluation": {
                        "path": _relative(args.private_report),
                        "sha256": sha256_file(args.private_report),
                    },
                },
            }
        )
        regression_report = _read_json(args.regression_report)
        public_freeze = {
            key: freeze.get(key)
            for key in (
                "schema_version",
                "status",
                "attempt_count",
                "started_at",
                "completed_at",
                "dataset_sha256",
                "regression_sha256",
                "application_sha256",
                "git",
                "policy",
                "model",
            )
        }
        summary = build_public_summary(
            regression_dataset=regression,
            regression_report=regression_report,
            holdout_dataset=dataset,
            holdout_report=report,
            ratings_paths=[args.regression_ratings, args.holdout_ratings],
            freeze=public_freeze,
        )
        _write_json(args.public_json, summary)
        args.public_markdown.parent.mkdir(parents=True, exist_ok=True)
        args.public_markdown.write_text(render_public_summary(summary), encoding="utf-8")
        freeze["reporting_artifacts"] = {
            "refreshed_at": now_iso(),
            "public_summary_json": {
                "path": _relative(args.public_json),
                "sha256": sha256_file(args.public_json),
            },
            "public_summary_markdown": {
                "path": _relative(args.public_markdown),
                "sha256": sha256_file(args.public_markdown),
            },
        }
        update_lock(args.lock, freeze)
        print(render_public_summary(summary))
        return 0
    except BaseException as exc:
        freeze.update(
            {
                "status": "FAILED_ATTEMPT_CONSUMED",
                "completed_at": now_iso(),
                "failure": {"type": type(exc).__name__, "message": str(exc)},
            }
        )
        update_lock(args.lock, freeze)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main(_parser().parse_args())))
