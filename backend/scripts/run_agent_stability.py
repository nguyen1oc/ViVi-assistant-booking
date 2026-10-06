"""Run or aggregate repeated benchmark trials for variance and observed pass@k."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.evaluation.agent_benchmark import (  # noqa: E402
    DEFAULT_DATABASE_CACHE,
    DEFAULT_GOLDEN_PATH,
    DEFAULT_NEGATIVE_PATH,
    _redact,
    judge_recorded_predictions,
    load_golden_dataset,
    merge_prediction_payloads,
    run_live_predictions,
    score_evaluation,
)
from src.evaluation.stability import aggregate_stability, render_stability_markdown  # noqa: E402


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    mode = command.add_mutually_exclusive_group(required=True)
    mode.add_argument("--live", action="store_true")
    mode.add_argument("--predictions", type=Path, action="append")
    mode.add_argument("--runs-input", type=Path)
    command.add_argument("--runs", type=int, default=3)
    command.add_argument("--case", action="append", dest="case_ids")
    command.add_argument("--llm-judge", action="store_true")
    command.add_argument(
        "--replacement-runs-input",
        type=Path,
        help="Optional targeted reruns; later records replace matching cases run by run.",
    )
    command.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN_PATH)
    command.add_argument("--negative-golden", type=Path, default=DEFAULT_NEGATIVE_PATH)
    command.add_argument("--database-cache", type=Path, default=DEFAULT_DATABASE_CACHE)
    command.add_argument("--eval-data-dir", type=Path)
    command.add_argument(
        "--runs-output",
        type=Path,
        default=PROJECT_ROOT / "eval" / "results" / "agent-stability-runs.json",
    )
    command.add_argument(
        "--json-output",
        type=Path,
        default=PROJECT_ROOT / "eval" / "results" / "agent-stability.json",
    )
    command.add_argument(
        "--markdown-output",
        type=Path,
        default=PROJECT_ROOT / "eval" / "results" / "agent-stability.md",
    )
    return command


async def run(args: argparse.Namespace) -> int:
    if args.runs < 2:
        raise ValueError("--runs must be at least 2")
    dataset = load_golden_dataset(args.golden)
    negative = json.loads(args.negative_golden.read_text(encoding="utf-8"))
    selected = set(args.case_ids or [])
    prediction_runs: list[dict[str, Any]] = []
    if args.live:
        for run_number in range(1, args.runs + 1):
            print(f"Starting independent benchmark run {run_number}/{args.runs}...", flush=True)
            prediction_runs.append(
                await run_live_predictions(
                    dataset,
                    database_cache=args.database_cache,
                    eval_data_dir=args.eval_data_dir,
                    case_ids=selected,
                    llm_judge=args.llm_judge,
                )
            )
            print(f"Completed independent benchmark run {run_number}/{args.runs}.", flush=True)
    else:
        if args.runs_input:
            runs_payload = json.loads(args.runs_input.read_text(encoding="utf-8"))
            prediction_runs = [dict(run) for run in runs_payload.get("runs", [])]
        else:
            paths = args.predictions or []
            prediction_runs = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
        if len(prediction_runs) < 2:
            raise ValueError("Supply at least two prediction runs")

        if args.replacement_runs_input:
            replacement_payload = json.loads(args.replacement_runs_input.read_text(encoding="utf-8"))
            replacement_runs = [dict(run) for run in replacement_payload.get("runs", [])]
            if len(replacement_runs) != len(prediction_runs):
                raise ValueError("Replacement run count must match the base run count")
            prediction_runs = [
                merge_prediction_payloads((base, replacement))
                for base, replacement in zip(prediction_runs, replacement_runs, strict=True)
            ]

        if args.llm_judge:
            for run_number, prediction in enumerate(prediction_runs, start=1):
                preliminary = score_evaluation(
                    dataset,
                    prediction,
                    dataset_path=args.golden,
                    negative_dataset=negative,
                )
                unscored = {
                    str(case["case_id"])
                    for case in preliminary["cases"]
                    if case.get("task_success") is None
                }
                print(
                    f"Judging {len(unscored)} previously unscored cases in run "
                    f"{run_number}/{len(prediction_runs)}...",
                    flush=True,
                )
                if unscored:
                    prediction_runs[run_number - 1] = await judge_recorded_predictions(
                        dataset,
                        prediction,
                        case_ids=unscored,
                    )

    reports = [
        score_evaluation(
            dataset,
            prediction,
            dataset_path=args.golden,
            negative_dataset=negative,
        )
        for prediction in prediction_runs
    ]
    stability = aggregate_stability(reports, selected_case_ids=selected or None)
    stability["scope"] = "selected_cases" if selected else "all_active_cases"
    stability["selected_case_ids"] = sorted(selected)
    args.runs_output.parent.mkdir(parents=True, exist_ok=True)
    args.runs_output.write_text(
        json.dumps(_redact({"runs": prediction_runs}), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.json_output.write_text(json.dumps(stability, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rendered = render_stability_markdown(stability)
    args.markdown_output.write_text(rendered, encoding="utf-8")
    print(rendered)
    return 0


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    return asyncio.run(run(parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
