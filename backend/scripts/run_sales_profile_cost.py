"""Measure live cost from the first booking chat through the stored sales brief."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.evaluation.agent_benchmark import (  # noqa: E402
    DEFAULT_DATABASE_CACHE,
    _estimate_model_costs,
    _redact,
    run_live_predictions,
    score_evaluation,
)

DEFAULT_PRICES = {
    "gpt-5.6-luna": (0.20, 1.20),
    "gpt-4o-mini": (0.15, 0.60),
}


def _dataset(case_count: int, case_numbers: list[int] | None = None) -> dict[str, Any]:
    cases = []
    indices = case_numbers or list(range(1, case_count + 1))
    for index in indices:
        case_id = f"SALES-PROFILE-COST-{index:03d}"
        cases.append(
            {
                "case_id": case_id,
                "source_case_ids": ["CONFIRM-001", "POSTBOOK-PROFILE-SIGNAL-001", "POSTBOOK-BOOKING-SIGNAL-001"],
                "turns": [
                    {
                        "role": "user",
                        "content": (
                            "Tôi muốn đặt lịch lái thử {{eval.vehicle_model_name}} tại "
                            "{{eval.showroom_name}} vào ngày {{eval.slot_date}}. "
                            "Hãy tìm các khung giờ còn trống."
                        ),
                    },
                    {
                        "role": "action",
                        "action": "search_options",
                        "payload": {
                            "vehicle_model": "{{eval.vehicle_model_name}}",
                            "showroom_id": "{{eval.showroom_id}}",
                            "preferred_date": "{{eval.slot_date}}",
                            "slot_limit": 30,
                        },
                        "content": "Chọn showroom, ngày và tải lịch trống",
                    },
                    {
                        "role": "action",
                        "action": "hold_slot",
                        "payload": {
                            "slot_id": "{{eval.slot_id}}",
                            "ui_action_id": f"hold:{case_id}",
                        },
                        "content": "Giữ khung giờ đã chọn",
                    },
                    {
                        "role": "action",
                        "action": "update_draft",
                        "payload": {
                            "booking_id": "{{action.booking_id}}",
                            "booker_patch": {
                                "full_name": "Nguyen Benchmark",
                                "email": "benchmark.booker@example.test",
                                "preferred_channel": "email",
                            },
                            "driver_same_as_booker": True,
                            "has_valid_license_commitment": True,
                            "expected_version": "{{action.version}}",
                        },
                        "content": "Điền thông tin người đặt và người lái",
                    },
                    {
                        "role": "action",
                        "action": "confirm_booking",
                        "payload": {
                            "booking_id": "{{action.booking_id}}",
                            "expected_version": "{{action.version}}",
                            "ui_action_id": f"confirm:{case_id}",
                        },
                        "content": "Xác nhận đặt lịch",
                    },
                    {
                        "role": "user",
                        "content": "Gia đình tôi có 4 người, hãy lưu ý để tư vấn buổi lái thử phù hợp.",
                    },
                    {
                        "role": "user",
                        "content": (
                            "Tôi thường đi cùng gia đình và ưu tiên không gian rộng, "
                            "an toàn cho trẻ nhỏ. Hãy lưu những thông tin này để tư vấn phù hợp."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            "Trong buổi lái thử này, tôi sẽ trực tiếp tham gia và lái xe; "
                            "có thêm 3 người trong gia đình đi cùng."
                        ),
                    },
                    {
                        "role": "portal",
                        "action": "generate_sales_brief",
                        "content": "Nhân viên sale mở profile và tạo Sales Brief cho booking",
                    },
                ],
                "ui_context": {"channel": "web", "locale": "vi-VN"},
                "expected": {
                    "intent": "advise",
                    "skill": "post_booking",
                    "tool": "update_post_booking_signals",
                    "arguments": {},
                    "argument_resolutions": {},
                    "allowed_extra_arguments": ["profile_signals", "booking_signals"],
                    "database_assertions": [
                        {"table": "bookings", "status": "confirmed"},
                        {
                            "assertion": "active_profile_signal",
                            "key": "household_size",
                            "value": 4,
                        },
                        {
                            "assertion": "active_booking_signal",
                            "key": "booker_attending",
                            "value": True,
                            "subject": "booker",
                        },
                        {
                            "assertion": "active_booking_signal",
                            "key": "booker_will_drive",
                            "value": True,
                            "subject": "booker",
                        },
                        {
                            "assertion": "active_booking_signal",
                            "key": "additional_guest_count",
                            "value": 3,
                            "subject": "group",
                        },
                        {
                            "assertion": "sales_brief_exists",
                            "minimum_length": 200,
                            "required_terms": ["4"],
                            "forbidden_terms": ["profile_", "booking_", "confidence", "source_type"],
                        },
                    ],
                    "response": {
                        "must_contain": [],
                        "forbidden_behaviors": ["leak_other_customer_pii"],
                    },
                },
                "tags": ["booking", "real_e2e", "post_booking", "sales_profile", "cost"],
                "review_status": "CURATED_SYNTHETIC_NOT_HUMAN_REVIEWED",
                "evaluation_status": "active",
                "known_gap": None,
                "evaluation_setup": {
                    "kind": "available_slot",
                    "vehicle_model": "VF 3",
                    "slot_offset_minutes": 20 + index,
                    "continue_to_sales_profile": True,
                },
            }
        )
    return {
        "schema_version": "1.2",
        "dataset_name": "vinfast_booking_to_sales_profile_cost_e2e",
        "dataset_version": "1.0.0",
        "description": "Live isolated flows from first booking chat through persisted sales brief.",
        "case_count": len(cases),
        "cases": cases,
    }


def _add_usage(target: dict[str, dict[str, int]], usage: Mapping[str, Any]) -> None:
    by_model = usage.get("by_model")
    if not isinstance(by_model, Mapping):
        return
    for model, values in by_model.items():
        if not isinstance(values, Mapping):
            continue
        row = target.setdefault(str(model), {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0})
        for key in row:
            row[key] += int(values.get(key) or 0)


def _phase_usage(predictions: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    phases: dict[str, dict[str, dict[str, int]]] = {
        "booking_chat": {},
        "post_booking_profile_chat": {},
        "sales_brief_generation": {},
    }
    for prediction in predictions.get("cases", []):
        confirmed = False
        for turn in prediction.get("turns", []):
            if turn.get("role") == "portal":
                phase = "sales_brief_generation"
            elif confirmed:
                phase = "post_booking_profile_chat"
            else:
                phase = "booking_chat"
            _add_usage(phases[phase], turn.get("token_usage") or {})
            if any(
                call.get("name") == "confirm_test_drive_booking" and call.get("status") == "success"
                for call in turn.get("tool_calls") or []
            ):
                confirmed = True

    result: dict[str, dict[str, Any]] = {}
    for phase, usage in phases.items():
        cost, breakdown, missing = _estimate_model_costs(usage, DEFAULT_PRICES)
        result[phase] = {
            "input_tokens": sum(row["input_tokens"] for row in usage.values()),
            "output_tokens": sum(row["output_tokens"] for row in usage.values()),
            "total_tokens": sum(row["total_tokens"] for row in usage.values()),
            "estimated_cost": cost,
            "model_cost_breakdown": breakdown,
            "unpriced_models": missing,
        }
    return result


def _full_flow_completed(prediction: Mapping[str, Any]) -> bool:
    return (
        not prediction.get("error")
        and prediction.get("sales_profile", {}).get("status") == "completed"
        and bool(prediction.get("sales_profile", {}).get("portal_profile_available"))
        and bool(prediction.get("database_assertions"))
        and all(check.get("passed") is True for check in prediction["database_assertions"])
    )


def _token_usage_complete(prediction: Mapping[str, Any]) -> bool:
    """Require an explicit signal that every LLM phase was observed."""
    return prediction.get("token_usage_observed") is True


def _render_cost_markdown(report: Mapping[str, Any]) -> str:
    metric = report["sales_profile_cost"]
    unique_flows = int(metric.get("unique_flows") or metric["attempted_flows"])
    no_attempts = int(metric["attempted_flows"]) == 0
    unavailable_average_reason = (
        "no workflow was attempted"
        if no_attempts
        else "at least one LLM phase did not expose token usage"
    )
    unavailable_token_reason = (
        "no workflow was attempted" if no_attempts else "token coverage is incomplete"
    )
    if no_attempts:
        unavailable_completed_reason = "no workflow was attempted"
    elif int(metric["completed_flows"]) == 0:
        unavailable_completed_reason = "no flow passed every completion assertion"
    else:
        unavailable_completed_reason = "token coverage is incomplete"
    lines = [
        "# Booking-to-Sales-Profile Cost Report",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "## Result",
        "",
        f"- Full-flow completion: **{metric['completed_flows']}/{unique_flows}**.",
        f"- Workflow attempts including retries: **{metric['attempted_flows']}**.",
        f"- Total observed LLM cost: **${metric['total_cost']:.9f}**.",
        "- Average per attempted full flow: "
        + (
            f"**${metric['average_cost_per_attempt']:.9f}**."
            if metric["average_cost_per_attempt"] is not None
            else f"**NOT AVAILABLE** because {unavailable_average_reason}."
        ),
        "- Cost per completed sales profile: "
        + (
            f"**${metric['cost_per_completed_sales_profile']:.9f}**."
            if metric["cost_per_completed_sales_profile"] is not None
            else f"**NOT AVAILABLE** because {unavailable_completed_reason}."
        ),
        "- Average tokens per attempt: "
        + (
            f"**{metric['tokens_per_attempt']:.1f}**."
            if metric["tokens_per_attempt"] is not None
            else f"**NOT AVAILABLE** because {unavailable_token_reason}."
        ),
        f"- Token measurement complete: **{'yes' if metric['cost_measurement_complete'] else 'no'}**.",
        "- Judge and infrastructure costs are excluded.",
        "",
        "## Measured workflow",
        "",
        "`chat/search → hold → customer details → confirm → post-booking profile signals → booking signals → sales portal → generated and stored Sales Brief`",
        "",
        "## Phase breakdown",
        "",
        "| Phase | Input tokens | Output tokens | Total tokens | Cost (USD) |",
        "|---|---:|---:|---:|---:|",
    ]
    for phase, usage in metric["phase_breakdown"].items():
        lines.append(
            f"| {phase} | {usage['input_tokens']} | {usage['output_tokens']} | "
            f"{usage['total_tokens']} | ${float(usage['estimated_cost'] or 0):.9f} |"
        )
    if metric.get("incomplete_reason"):
        lines.extend(["", f"> {metric['incomplete_reason']}"])
    lines.extend(
        [
            "",
            "## Cases",
            "",
            "| Case | Full flow | Token usage complete | Failed assertions |",
            "|---|---:|---:|---|",
        ]
    )
    for case in metric["cases"]:
        failed = ", ".join(case["failed_assertions"]) or "-"
        lines.append(
            f"| {case['case_id']} | {'PASS' if case['completed'] else 'FAIL'} | "
            f"{'yes' if case['token_usage_complete'] else 'no'} | {failed} |"
        )
    lines.extend(
        [
            "",
            "## Pricing basis",
            "",
            "Observed provider token metadata × explicitly supplied project rates: "
            "`gpt-5.6-luna $0.20/$1.20` and `gpt-4o-mini $0.15/$0.60` per million input/output tokens.",
        ]
    )
    return "\n".join(lines) + "\n"


async def run(args: argparse.Namespace) -> int:
    dataset = _dataset(args.cases, args.case_numbers)
    expected_case_count = len(dataset["cases"])
    args.output_dir.mkdir(parents=True, exist_ok=True)
    golden_path = args.output_dir / f"{args.prefix}-golden.json"
    predictions_path = args.output_dir / f"{args.prefix}-predictions.json"
    report_path = args.output_dir / f"{args.prefix}-report.json"
    markdown_path = args.output_dir / f"{args.prefix}-report.md"
    golden_path.write_text(json.dumps(dataset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.predictions_input:
        predictions = json.loads(args.predictions_input.read_text(encoding="utf-8"))
        selected_ids = {str(case["case_id"]) for case in dataset["cases"]}
        predictions = {
            **predictions,
            "cases": [
                case for case in predictions.get("cases", []) if str(case.get("case_id")) in selected_ids
            ],
        }
    else:
        predictions = await run_live_predictions(
            dataset,
            database_cache=args.database_cache,
            eval_data_dir=args.eval_data_dir,
        )
    predictions_path.write_text(
        json.dumps(_redact(predictions), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    scored = score_evaluation(
        dataset,
        predictions,
        dataset_path=golden_path,
        negative_dataset={"cases": []},
        model_prices=DEFAULT_PRICES,
    )
    attempted = len(predictions.get("cases", []))
    completed = sum(_full_flow_completed(item) for item in predictions.get("cases", []))
    token_complete_cases = sum(
        _token_usage_complete(item) for item in predictions.get("cases", [])
    )
    cost_measurement_complete = (
        attempted == expected_case_count and token_complete_cases == attempted
    )
    if not attempted:
        measurement_status = "NOT_RUN"
        incomplete_reason = "No full-flow attempt was executed."
    elif attempted != expected_case_count:
        measurement_status = "PARTIAL"
        incomplete_reason = (
            f"Only {attempted}/{expected_case_count} requested workflows were executed."
        )
    elif token_complete_cases != attempted:
        measurement_status = "PARTIAL"
        incomplete_reason = (
            "Cost is an observed lower bound only: Sales Brief generation does not expose "
            "token callbacks in the current runtime. Add optional config/callback support "
            "to summarize_user_profile before reporting cost per completed Sales Profile."
        )
    else:
        measurement_status = "COMPLETE"
        incomplete_reason = None
    phase_breakdown = _phase_usage(predictions)
    total_cost = sum(float(phase.get("estimated_cost") or 0) for phase in phase_breakdown.values())
    total_tokens = int(scored.get("usage", {}).get("total_tokens") or 0)
    dataset_cases = {case["case_id"]: case for case in dataset["cases"]}
    case_results = []
    for prediction in predictions.get("cases", []):
        expected_assertions = dataset_cases[prediction["case_id"]]["expected"]["database_assertions"]
        failed = []
        for index, check in enumerate(prediction.get("database_assertions") or []):
            if check.get("passed") is not True:
                assertion = expected_assertions[index]
                label = str(assertion.get("assertion") or assertion.get("table") or index)
                if assertion.get("key"):
                    label += f":{assertion['key']}"
                failed.append(label)
        if prediction.get("error"):
            failed.append(str(prediction["error"]))
        case_results.append(
            {
                "case_id": prediction["case_id"],
                "completed": _full_flow_completed(prediction),
                "token_usage_complete": _token_usage_complete(prediction),
                "failed_assertions": failed,
            }
        )
    scored["sales_profile_cost"] = {
        "status": measurement_status,
        "currency": "USD",
        "attempted_flows": attempted,
        "completed_flows": completed,
        "total_cost": total_cost,
        "average_cost_per_attempt": (
            total_cost / attempted if attempted and cost_measurement_complete else None
        ),
        "cost_per_completed_sales_profile": (
            total_cost / completed if completed and cost_measurement_complete else None
        ),
        "total_tokens": total_tokens,
        "tokens_per_attempt": (
            total_tokens / attempted if attempted and cost_measurement_complete else None
        ),
        "cost_measurement_complete": cost_measurement_complete,
        "token_complete_flows": token_complete_cases,
        "incomplete_reason": incomplete_reason,
        "measurement_method": "total_observed_llm_cost_from_first_chat_through_stored_sales_brief",
        "phase_breakdown": phase_breakdown,
        "cases": case_results,
        "exclusions": ["judge", "email/SMS/Zalo", "Redis/DB/hosting infrastructure"],
    }
    if args.base_report:
        base_report = json.loads(args.base_report.read_text(encoding="utf-8"))
        base_metric = base_report["sales_profile_cost"]
        current_metric = scored["sales_profile_cost"]
        combined_cases = {case["case_id"]: dict(case) for case in base_metric["cases"]}
        combined_cases.update({case["case_id"]: dict(case) for case in current_metric["cases"]})
        combined_phases: dict[str, dict[str, Any]] = {}
        phase_names = [
            "booking_chat",
            "post_booking_profile_chat",
            "sales_brief_generation",
        ]
        phase_names.extend(
            sorted(
                (set(base_metric["phase_breakdown"]) | set(current_metric["phase_breakdown"]))
                - set(phase_names)
            )
        )
        for phase in phase_names:
            base_phase = base_metric["phase_breakdown"].get(phase, {})
            current_phase = current_metric["phase_breakdown"].get(phase, {})
            combined_phases[phase] = {
                key: float(base_phase.get(key) or 0) + float(current_phase.get(key) or 0)
                for key in ("input_tokens", "output_tokens", "total_tokens", "estimated_cost")
            }
            for token_key in ("input_tokens", "output_tokens", "total_tokens"):
                combined_phases[phase][token_key] = int(combined_phases[phase][token_key])
        combined_attempts = int(base_metric["attempted_flows"]) + int(current_metric["attempted_flows"])
        combined_cost = sum(float(phase["estimated_cost"]) for phase in combined_phases.values())
        combined_tokens = int(base_metric["total_tokens"]) + int(current_metric["total_tokens"])
        completed_unique = sum(case.get("completed") is True for case in combined_cases.values())
        combined_cost_measurement_complete = (
            base_metric.get("cost_measurement_complete") is True
            and current_metric.get("cost_measurement_complete") is True
        )
        scored["sales_profile_cost"] = {
            **current_metric,
            "status": "COMPLETE" if combined_cost_measurement_complete else "PARTIAL",
            "attempted_flows": combined_attempts,
            "unique_flows": len(combined_cases),
            "retry_attempts": combined_attempts - len(combined_cases),
            "completed_flows": completed_unique,
            "total_cost": combined_cost,
            "average_cost_per_attempt": (
                combined_cost / combined_attempts
                if combined_attempts and combined_cost_measurement_complete
                else None
            ),
            "cost_per_completed_sales_profile": (
                combined_cost / completed_unique
                if completed_unique and combined_cost_measurement_complete
                else None
            ),
            "total_tokens": combined_tokens,
            "tokens_per_attempt": (
                combined_tokens / combined_attempts
                if combined_attempts and combined_cost_measurement_complete
                else None
            ),
            "tokens_per_completed_sales_profile": (
                combined_tokens / completed_unique
                if completed_unique and combined_cost_measurement_complete
                else None
            ),
            "cost_measurement_complete": combined_cost_measurement_complete,
            "token_complete_flows": sum(
                case.get("token_usage_complete") is True
                for case in combined_cases.values()
            ),
            "incomplete_reason": (
                None
                if combined_cost_measurement_complete
                else current_metric.get("incomplete_reason")
                or base_metric.get("incomplete_reason")
                or "Token coverage is incomplete for at least one combined attempt."
            ),
            "phase_breakdown": combined_phases,
            "cases": [combined_cases[key] for key in sorted(combined_cases)],
            "retry_base_report": str(args.base_report),
        }
    if args.base_predictions or args.base_golden:
        if not args.base_predictions or not args.base_golden:
            raise ValueError("--base-predictions and --base-golden must be supplied together")
        base_predictions = json.loads(args.base_predictions.read_text(encoding="utf-8"))
        merged_predictions = dict(base_predictions)
        merged_cases = {
            str(case["case_id"]): dict(case)
            for case in base_predictions.get("cases", [])
        }
        merged_cases.update(
            {str(case["case_id"]): dict(case) for case in predictions.get("cases", [])}
        )
        merged_predictions.update(
            {
                "generated_at": predictions.get("generated_at"),
                "mode": "live+targeted-retry",
                "cases": [merged_cases[key] for key in sorted(merged_cases)],
                "retry_attempts": int(scored["sales_profile_cost"].get("retry_attempts") or 0),
            }
        )
        merged_dataset = json.loads(args.base_golden.read_text(encoding="utf-8"))
        golden_path.write_text(
            json.dumps(merged_dataset, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        predictions_path.write_text(
            json.dumps(_redact(merged_predictions), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        combined_metric = scored["sales_profile_cost"]
        scored = score_evaluation(
            merged_dataset,
            merged_predictions,
            dataset_path=golden_path,
            negative_dataset={"cases": []},
            model_prices=DEFAULT_PRICES,
        )
        scored["sales_profile_cost"] = combined_metric
    report_path.write_text(json.dumps(_redact(scored), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown = _render_cost_markdown(scored)
    markdown_path.write_text(markdown, encoding="utf-8")
    print(markdown)
    return 0


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    command.add_argument("--cases", type=int, default=10)
    command.add_argument("--case-number", type=int, action="append", dest="case_numbers")
    command.add_argument("--prefix", default="booking-to-sales-profile-cost-10")
    command.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "artifacts" / "agent-evaluation",
    )
    command.add_argument("--database-cache", type=Path, default=DEFAULT_DATABASE_CACHE)
    command.add_argument("--eval-data-dir", type=Path)
    command.add_argument("--base-report", type=Path)
    command.add_argument("--predictions-input", type=Path)
    command.add_argument("--base-predictions", type=Path)
    command.add_argument("--base-golden", type=Path)
    return command


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    return asyncio.run(run(parser().parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
