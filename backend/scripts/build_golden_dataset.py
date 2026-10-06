"""Build the structured agent golden dataset from the review-friendly CSV."""

from __future__ import annotations

import argparse
import copy
import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = PROJECT_ROOT / "eval" / "data"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "eval" / "golden"
DEFAULT_REGRESSION_PATH = DEFAULT_OUTPUT_DIR / "regression_cases.csv"
DEFAULT_CHALLENGE_PATH = DEFAULT_OUTPUT_DIR / "challenge_cases.csv"
DEFAULT_NEGATIVE_SOURCE_PATH = DEFAULT_OUTPUT_DIR / "negative_cases.csv"
JSON_COLUMNS: dict[str, type] = {
    "turns_json": list,
    "ui_context_json": dict,
    "expected_arguments_json": dict,
    "expected_db_assertions_json": list,
    "response_must_contain_json": list,
    "forbidden_json": list,
    "tags_json": list,
}
TOOL_ALIASES = {"verify_booking_access_otp": "verify_booking_access"}
ACTIVE_AGENT_TOOLS = {
    "cancel_booking",
    "confirm_test_drive_booking",
    "get_booking_details",
    "get_booking_draft",
    "hold_test_drive_slot",
    "request_booking_access",
    "reschedule_booking",
    "search_knowledge",
    "search_test_drive_options",
    "update_booking_draft",
    "update_post_booking_signals",
    "verify_booking_access",
}
KNOWN_GAPS: dict[str, str] = {}
KNOWN_GAP_CASES: dict[str, str] = {}
SEARCH_CASE_MODELS = {
    "SEARCH-001": "VF 3",
    "SEARCH-002": "VF 5",
    "SEARCH-003": "VF 6",
    "SEARCH-004": "VF 6",
    "SEARCH-005": "VF 7",
    "SEARCH-006": "VF 7",
    "SEARCH-007": "VF 7",
    "SEARCH-008": "VF 8",
    "SEARCH-009": "VF 8",
    "SEARCH-010": "VF 9",
}
ALLOWED_EXTRA_ARGUMENTS_BY_TOOL = {
    "get_booking_details": ["access_session_token", "booking_id", "booking_code"],
    "hold_test_drive_slot": ["ui_action_id"],
    "search_knowledge": ["market", "model_code", "query", "topics"],
    "search_test_drive_options": ["address", "showroom_limit", "slot_limit"],
    "update_post_booking_signals": ["booking_signals", "profile_signals"],
}


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description="Build the tracked eval/golden JSON datasets.")
    command.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    command.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    command.add_argument("--check", action="store_true", help="Fail if either generated JSON file is not current.")
    return command


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _parse_json(case_id: str, column: str, value: str, expected_type: type) -> Any:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as error:
        raise SystemExit(f"{case_id}: invalid {column}: {error}") from error
    if not isinstance(parsed, expected_type):
        raise SystemExit(f"{case_id}: {column} must contain a JSON {expected_type.__name__}")
    return parsed


def _current_showroom_id(public_source_id: str) -> str:
    match = re.fullmatch(r"VFVN_(\d+)", public_source_id.strip())
    if not match:
        raise SystemExit(f"Invalid public showroom id: {public_source_id!r}")
    return str(int(match.group(1)))


def _showroom_context(data_dir: Path) -> tuple[dict[str, str], dict[str, str], set[str]]:
    hanoi_rows = _read_csv(data_dir / "reference" / "showrooms_hanoi_demo_47.csv")
    hanoi_mapping = {row["id"]: _current_showroom_id(row["public_source_id"]) for row in hanoi_rows}
    hanoi_names = {row["id"]: row["name"] for row in hanoi_rows}
    active_showroom_ids = {
        row["id"] for row in _read_csv(data_dir / "seed" / "04_showrooms.csv") if row["is_active"] == "1"
    }
    return hanoi_mapping, hanoi_names, active_showroom_ids


def _eligible_demo_inventory(data_dir: Path) -> set[tuple[str, str]]:
    model_codes = {row["id"]: row["code"] for row in _read_csv(data_dir / "seed" / "08_vehicle_models.csv")}
    variant_models = {
        row["id"]: model_codes[row["model_id"]] for row in _read_csv(data_dir / "seed" / "09_vehicle_variants.csv")
    }
    return {
        (row["showroom_id"], variant_models[row["variant_id"]])
        for row in _read_csv(data_dir / "seed" / "10_demo_vehicles.csv")
        if row["is_active"] == "1"
        and row["operational_status"] == "available"
        and row["battery_soc"]
        and float(row["battery_soc"]) >= float(row["minimum_booking_soc"])
    }


def _replace_showroom_ids(value: Any, mapping: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {
            key: mapping.get(item, item)
            if key == "showroom_id" and isinstance(item, str)
            else _replace_showroom_ids(item, mapping)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_replace_showroom_ids(item, mapping) for item in value]
    return value


def _replace_showroom_aliases(value: Any, names: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {key: _replace_showroom_aliases(item, names) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_showroom_aliases(item, names) for item in value]
    if isinstance(value, str):
        return re.sub(r"\bHN\d{3}\b", lambda match: names.get(match.group(0), match.group(0)), value)
    return value


def _normalize_arguments(tool: str | None, arguments: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(arguments)
    if tool == "verify_booking_access" and "otp" in normalized:
        normalized["otp_code"] = normalized.pop("otp")
    return normalized


def _workflow_turn(action: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "role": "action",
        "action": action,
        "payload": payload,
        "content": f"Thực hiện thao tác {action}",
    }


def _apply_executable_contract(case: dict[str, Any]) -> None:
    """Add the runtime state that stateful golden cases need to be executable.

    The review CSV intentionally stays compact. This compiler step makes the
    otherwise implicit UI/DB preconditions explicit in the tracked JSON.
    """
    case_id = case["case_id"]
    expected = case["expected"]
    tool = expected["tool"]
    tags = set(case.get("tags", []))

    if case_id.startswith("POSTBOOK-"):
        setup: dict[str, Any] = {
            "kind": "post_booking",
            "vehicle_model": "VF 8",
            "participant_role": "booker",
            "slot_offset_minutes": 500 + len(case_id),
        }
        if case_id == "POSTBOOK-CONTEXT-001":
            setup["booking_signals"] = [
                {
                    "category": "attendance",
                    "key": "booker_attending",
                    "value": True,
                    "subject": "booker",
                    "certainty": "known",
                    "confidence": 1.0,
                    "source_type": "explicit_user",
                    "operation": "add",
                },
                {
                    "category": "driving",
                    "key": "booker_will_drive",
                    "value": True,
                    "subject": "booker",
                    "certainty": "known",
                    "confidence": 1.0,
                    "source_type": "explicit_user",
                    "operation": "add",
                },
            ]
        case["evaluation_setup"] = setup
        return

    if case_id in SEARCH_CASE_MODELS:
        vehicle_model = SEARCH_CASE_MODELS[case_id]
        showroom_resolution = expected["argument_resolutions"]["showroom_id"]
        showroom_name = str(showroom_resolution["accepted_values"][0])
        expected["arguments"]["vehicle_model"] = vehicle_model
        expected["response"]["must_contain"] = [showroom_name]
        case["turns"] = [
            {
                "role": "user",
                "content": f"Tôi muốn lái thử {vehicle_model} ở {showroom_name}",
            }
        ]
        return

    if tool == "hold_test_drive_slot":
        vehicle_model = str(expected["arguments"].pop("vehicle_model"))
        case["evaluation_setup"] = {
            "kind": "available_slot",
            "vehicle_model": vehicle_model,
            "slot_offset_minutes": int(case_id.rsplit("-", 1)[1]) * 7,
        }
        case["ui_context"] = {
            "channel": "booking",
            "stage": "choose_slot",
            "selectedVehicle": {"id": "{{eval.vehicle_model_id}}", "name": "{{eval.vehicle_model_name}}"},
            "selectedShowroom": {"id": "{{eval.showroom_id}}", "name": "{{eval.showroom_name}}"},
        }
        case["turns"] = [
            {
                "role": "user",
                "content": (
                    "Giữ giúp tôi khung {{eval.slot_time}} ngày {{eval.slot_date}} cho "
                    "{{eval.vehicle_model_name}} tại {{eval.showroom_name}}"
                ),
            }
        ]
        expected["arguments"] = {"slot_id": "{{eval.slot_id}}"}
        return

    if case_id.startswith("CONFLICT-"):
        case["evaluation_setup"] = {"kind": "available_slot", "vehicle_model": "VF 3"}
        case["turns"] = [
            {"role": "fixture", "action": "reserve_eval_slot"},
            _workflow_turn(
                "hold_slot",
                {"slot_id": "{{eval.slot_id}}", "ui_action_id": "hold:eval-conflict"},
            ),
        ]
        expected.update(
            {
                "intent": "hold_slot",
                "tool": "hold_test_drive_slot",
                "arguments": {
                    "slot_id": "{{eval.slot_id}}",
                    "ui_action_id": "hold:eval-conflict",
                },
                "database_assertions": [{"expect_error": "SLOT_NO_LONGER_AVAILABLE"}],
                "response": {
                    "must_contain": ["không còn khả dụng"],
                    "forbidden_behaviors": ["double_book_slot", "overwrite_existing_hold"],
                },
            }
        )
        return

    if tool == "confirm_test_drive_booking" and "hold_expired" not in tags:
        case["evaluation_setup"] = {"kind": "available_slot", "vehicle_model": "VF 3"}
        case["turns"] = [
            _workflow_turn(
                "hold_slot",
                {"slot_id": "{{eval.slot_id}}", "ui_action_id": "hold:eval-confirm"},
            ),
            _workflow_turn(
                "update_draft",
                {
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
            ),
            _workflow_turn(
                "confirm_booking",
                {
                    "booking_id": "{{action.booking_id}}",
                    "expected_version": "{{action.version}}",
                    "ui_action_id": "confirm:eval-confirm",
                },
            ),
        ]
        expected["arguments"] = {
            "booking_id": "{{action.booking_id}}",
            "expected_version": "{{action.version}}",
            "ui_action_id": "confirm:eval-confirm",
        }
        return

    if tool == "cancel_booking":
        case["evaluation_setup"] = {
            "kind": "confirmed_booking",
            "vehicle_model": "VF 3",
            "slot_offset_minutes": 131,
        }
        case["turns"] = [
            _workflow_turn(
                "cancel_booking",
                {
                    "booking_id": "{{eval.current_booking_id}}",
                    "access_session_token": "{{eval.access_session_token}}",
                    "ui_action_id": "cancel:eval-cancel",
                    "reason": "Thay đổi kế hoạch",
                },
            )
        ]
        expected["arguments"] = {
            "booking_id": "{{eval.current_booking_id}}",
            "access_session_token": "{{eval.access_session_token}}",
            "ui_action_id": "cancel:eval-cancel",
        }
        expected["allowed_extra_arguments"] = ["reason"]
        return

    if tool == "reschedule_booking":
        case["evaluation_setup"] = {
            "kind": "confirmed_booking_reschedule",
            "vehicle_model": "VF 3",
            "slot_offset_minutes": 149,
        }
        case["turns"] = [
            _workflow_turn(
                "reschedule_booking",
                {
                    "current_booking_id": "{{eval.current_booking_id}}",
                    "new_slot_id": "{{eval.new_slot_id}}",
                    "access_session_token": "{{eval.access_session_token}}",
                    "ui_action_id": "reschedule:eval-reschedule",
                },
            )
        ]
        expected["arguments"] = {
            "current_booking_id": "{{eval.current_booking_id}}",
            "new_slot_id": "{{eval.new_slot_id}}",
            "access_session_token": "{{eval.access_session_token}}",
            "ui_action_id": "reschedule:eval-reschedule",
        }
        expected["database_assertions"] = [
            {"table": "bookings", "old_status": "rescheduled"},
            {"table": "bookings", "new_status": "confirmed"},
            {"table": "test_drive_slots", "status": "booked"},
        ]
        return

    if tool == "confirm_test_drive_booking" and "hold_expired" in tags:
        case["evaluation_setup"] = {"kind": "available_slot", "vehicle_model": "VF 3"}
        case["turns"] = [
            _workflow_turn(
                "hold_slot",
                {"slot_id": "{{eval.slot_id}}", "ui_action_id": "hold:eval-expired"},
            ),
            {"role": "fixture", "action": "expire_latest_hold"},
            _workflow_turn(
                "confirm_booking",
                {
                    "booking_id": "{{action.booking_id}}",
                    "expected_version": "{{action.version}}",
                    "ui_action_id": "confirm:eval-expired",
                },
            ),
        ]
        expected["arguments"] = {
            "booking_id": "{{action.booking_id}}",
            "expected_version": "{{action.version}}",
            "ui_action_id": "confirm:eval-expired",
        }
        return

    if case_id.startswith("OTP_BAD-"):
        case["turns"] = [
            _workflow_turn(
                "request_access",
                {
                    "contact_value": "person.000001@example.test",
                    "purpose": "manage",
                    "preferred_channel": "email",
                },
            ),
            _workflow_turn(
                "verify_access",
                {"challenge_id": "{{action.challenge_id}}", "otp_code": "{{invalid_mock_otp}}"},
            ),
        ]
        expected["arguments"] = {
            "challenge_id": "{{action.challenge_id}}",
            "otp_code": "{{invalid_mock_otp}}",
        }
        expected["database_assertions"] = [
            {"table": "otp_challenges", "attempt_count": "increment"},
            {"expect_error": "OTP_INVALID"},
        ]
        return

    if case_id.startswith("OTP_EXPIRED-"):
        case["turns"] = [
            _workflow_turn(
                "request_access",
                {
                    "contact_value": "person.000001@example.test",
                    "purpose": "manage",
                    "preferred_channel": "email",
                },
            ),
            {"role": "fixture", "action": "expire_latest_otp"},
            _workflow_turn(
                "verify_access",
                {"challenge_id": "{{action.challenge_id}}", "otp_code": "{{latest_mock_otp}}"},
            ),
        ]
        expected["arguments"] = {
            "challenge_id": "{{action.challenge_id}}",
            "otp_code": "{{latest_mock_otp}}",
        }
        return

    if case_id == "MODEL-NOT-IN-SHOWROOM-001":
        case["turns"] = [
            {
                "role": "user",
                "content": "Tôi muốn lái thử VF 7 ở VinFast Thăng Long Trịnh Văn Bô",
            }
        ]
        expected["arguments"]["vehicle_model"] = "VF 7"
        expected["database_assertions"] = [{"assertion": "requested_showroom_has_no_eligible_vehicle"}]
        return

    if case_id == "MODEL-UNSUPPORTED-001":
        expected["database_assertions"] = [{"expect_error": "VEHICLE_NOT_FOUND"}]
        return

    if case_id == "STAFF-CAPACITY-001":
        expected["arguments"]["preferred_time"] = expected["arguments"].pop("time")
        expected["arguments"]["vehicle_model"] = "VF 3"
        expected["database_assertions"] = [{"assertion": "offered_slots_within_staff_capacity"}]
        case["turns"] = [
            _workflow_turn(
                "search_options",
                {
                    "vehicle_model": "VF 3",
                    "showroom_id": expected["arguments"]["showroom_id"],
                    "preferred_time": expected["arguments"]["preferred_time"],
                    "slot_limit": 100,
                },
            )
        ]
        expected["allowed_extra_arguments"] = ["slot_limit"]
        return

    if case_id == "BOOK-FOR-OTHER-001":
        expected.update(
            {
                "intent": "search_options",
                "tool": "search_test_drive_options",
                "arguments": {"vehicle_model": "VF 7"},
                "allowed_extra_arguments": list(ALLOWED_EXTRA_ARGUMENTS_BY_TOOL["search_test_drive_options"]),
                "database_assertions": [],
            }
        )


def _validate_case(
    case: dict[str, Any],
    active_showroom_ids: set[str],
    eligible_demo_inventory: set[tuple[str, str]],
) -> None:
    case_id = case["case_id"]
    turns = case["turns"]
    if not turns:
        raise SystemExit(f"{case_id}: at least one conversation turn is required")
    for turn in turns:
        if not isinstance(turn, dict):
            raise SystemExit(f"{case_id}: invalid conversation turn: {turn!r}")
        role = turn.get("role")
        valid_message = role in {"user", "assistant"} and bool(turn.get("content"))
        valid_action = role == "action" and bool(turn.get("action")) and isinstance(turn.get("payload"), dict)
        valid_fixture = role == "fixture" and turn.get("action") in {
            "expire_latest_hold",
            "expire_latest_otp",
            "reserve_eval_slot",
        }
        if not (valid_message or valid_action or valid_fixture):
            raise SystemExit(f"{case_id}: invalid conversation turn: {turn!r}")

    expected = case["expected"]
    if not expected["intent"] or not expected["skill"]:
        raise SystemExit(f"{case_id}: expected intent and skill are required")
    if expected["tool"] is None and expected["intent"] not in {"advise", "guardrail"}:
        raise SystemExit(f"{case_id}: only advisory or guardrail cases may omit the expected tool")
    if case["evaluation_status"] == "active" and expected["tool"] not in ACTIVE_AGENT_TOOLS | {None}:
        raise SystemExit(f"{case_id}: active case references unavailable tool {expected['tool']!r}")
    if (
        case["evaluation_status"] == "known_gap"
        and expected["tool"] not in KNOWN_GAPS
        and case_id not in KNOWN_GAP_CASES
    ):
        raise SystemExit(f"{case_id}: known gap has no explanation for tool {expected['tool']!r}")
    showroom_id = expected["arguments"].get("showroom_id")
    if showroom_id and showroom_id not in active_showroom_ids:
        raise SystemExit(f"{case_id}: showroom {showroom_id!r} is not active in the PostgreSQL baseline")
    if case_id in SEARCH_CASE_MODELS:
        model_code = re.sub(r"[\s_-]+", "", str(expected["arguments"]["vehicle_model"]))
        if (str(showroom_id), model_code) not in eligible_demo_inventory:
            raise SystemExit(f"{case_id}: direct-search showroom {showroom_id!r} has no eligible {model_code} demo")


def _expand_positive_booking_funnel(cases: list[dict[str, Any]]) -> int:
    """Add independent end-to-end confirmations instead of a one-case denominator."""
    template = next((case for case in cases if case["case_id"] == "CONFIRM-001"), None)
    if template is None:
        raise SystemExit("CONFIRM-001 is required to build the positive booking funnel")
    created = 0
    for index in range(2, 11):
        suffix = f"{index:03d}"
        case = copy.deepcopy(template)
        case["case_id"] = f"CONFIRM-E2E-{suffix}"
        case["source_case_ids"] = [case["case_id"]]
        case["evaluation_setup"]["slot_offset_minutes"] = 200 + index * 13
        case["tags"] = sorted(set(case.get("tags", [])) | {"positive_funnel"})
        for turn in case["turns"]:
            payload = turn.get("payload")
            if not isinstance(payload, dict):
                continue
            if isinstance(payload.get("ui_action_id"), str):
                payload["ui_action_id"] = payload["ui_action_id"].replace(
                    "eval-confirm",
                    f"eval-confirm-{suffix}",
                )
            booker_patch = payload.get("booker_patch")
            if isinstance(booker_patch, dict):
                booker_patch["email"] = f"benchmark.booker+{suffix}@example.test"
        case["expected"]["arguments"]["ui_action_id"] = f"confirm:eval-confirm-{suffix}"
        cases.append(case)
        created += 1
    return created


def build(data_dir: Path) -> dict[str, Any]:
    fixtures_dir = data_dir / "fixtures"
    source_rows = [
        *_read_csv(fixtures_dir / "golden_agent_cases.csv"),
        *_read_csv(DEFAULT_REGRESSION_PATH),
        *_read_csv(DEFAULT_CHALLENGE_PATH),
    ]
    if not source_rows:
        raise SystemExit("Golden dataset source CSV is empty")
    hanoi_mapping, hanoi_names, active_showroom_ids = _showroom_context(data_dir)
    eligible_demo_inventory = _eligible_demo_inventory(data_dir)
    seen: set[str] = set()
    excluded_source_case_count = 0
    cases: list[dict[str, Any]] = []
    case_by_semantics: dict[str, dict[str, Any]] = {}

    for row in source_rows:
        case_id = row["case_id"].strip()
        if not case_id or case_id in seen:
            raise SystemExit(f"Golden case id is empty or duplicated: {case_id!r}")
        seen.add(case_id)
        if row["expected_skill"].strip() == "advise":
            excluded_source_case_count += 1
            continue
        parsed = {
            column: _parse_json(case_id, column, row[column], expected_type)
            for column, expected_type in JSON_COLUMNS.items()
        }
        tags = list(parsed["tags_json"])
        if case_id.startswith("SEARCH-") and "groundedness" not in tags:
            tags.append("groundedness")
        tool = TOOL_ALIASES.get(row["expected_tool"].strip(), row["expected_tool"].strip()) or None
        original_arguments = parsed["expected_arguments_json"]
        arguments = _normalize_arguments(
            tool,
            _replace_showroom_ids(original_arguments, hanoi_mapping),
        )
        argument_resolutions: dict[str, Any] = {}
        source_showroom_id = original_arguments.get("showroom_id")
        if isinstance(source_showroom_id, str) and source_showroom_id in hanoi_names:
            argument_resolutions["showroom_id"] = {
                "source_field": "showroom_query",
                "accepted_values": [hanoi_names[source_showroom_id]],
            }
        skill = row["expected_skill"].strip()
        evaluation_status = "known_gap" if tool in KNOWN_GAPS or case_id in KNOWN_GAP_CASES else "active"
        case = {
            "case_id": case_id,
            "source_case_ids": [case_id],
            "turns": _replace_showroom_aliases(parsed["turns_json"], hanoi_names),
            "ui_context": parsed["ui_context_json"],
            "expected": {
                "intent": row["expected_intent"].strip(),
                "skill": skill,
                "tool": tool,
                "arguments": arguments,
                "argument_resolutions": argument_resolutions,
                "allowed_extra_arguments": list(ALLOWED_EXTRA_ARGUMENTS_BY_TOOL.get(tool, [])),
                "database_assertions": parsed["expected_db_assertions_json"],
                "response": {
                    "must_contain": parsed["response_must_contain_json"],
                    "forbidden_behaviors": parsed["forbidden_json"],
                },
            },
            "tags": tags,
            "review_status": row["review_status"].strip(),
            "evaluation_status": evaluation_status,
            "known_gap": KNOWN_GAPS.get(tool) or KNOWN_GAP_CASES.get(case_id),
        }
        _apply_executable_contract(case)
        _validate_case(case, active_showroom_ids, eligible_demo_inventory)
        semantic_value = {key: value for key, value in case.items() if key not in {"case_id", "source_case_ids"}}
        semantic_key = json.dumps(semantic_value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if semantic_key in case_by_semantics:
            case_by_semantics[semantic_key]["source_case_ids"].append(case_id)
        else:
            case_by_semantics[semantic_key] = case
            cases.append(case)

    deduplicated_case_count = len(cases)
    generated_booking_funnel_case_count = _expand_positive_booking_funnel(cases)
    metadata = json.loads((data_dir / "GENERATION_METADATA.json").read_text(encoding="utf-8"))
    review_summary = Counter(case["review_status"] for case in cases)
    evaluation_summary = Counter(case["evaluation_status"] for case in cases)
    return {
        "schema_version": "1.2",
        "dataset_name": "vinfast_booking_agent_golden",
        "dataset_version": metadata["dataset_version"],
        "language": "vi-VN",
        "case_count": len(cases),
        "source_case_count": len(source_rows) - excluded_source_case_count,
        "excluded_source_case_count": excluded_source_case_count,
        "deduplicated_source_case_count": (len(source_rows) - excluded_source_case_count - deduplicated_case_count),
        "generated_booking_funnel_case_count": generated_booking_funnel_case_count,
        "review_status_summary": dict(sorted(review_summary.items())),
        "evaluation_status_summary": dict(sorted(evaluation_summary.items())),
        "challenge_case_count": sum("challenge" in case.get("tags", []) for case in cases),
        "human_review_required": any("NOT_HUMAN_REVIEWED" in case["review_status"] for case in cases),
        "baseline": {
            "source_of_truth": metadata["source_of_truth"],
            "showroom_count": metadata["showroom_count"],
            "active_staff_count": metadata["active_staff_count"],
            "booking_count": metadata["booking_count"],
        },
        "provenance": {
            "source_files": [
                "eval/data/fixtures/golden_agent_cases.csv",
                "eval/golden/regression_cases.csv",
                "eval/golden/challenge_cases.csv",
            ],
            "showroom_aliases": "eval/data/reference/showrooms_hanoi_demo_47.csv",
            "note": (
                "Rows outside current product scope are excluded before semantic deduplication; retained duplicate IDs "
                "remain in source_case_ids. Challenge-tagged cases form a separately reported difficult slice."
            ),
        },
        "cases": cases,
    }


def build_negative_cases(data_dir: Path) -> dict[str, Any]:
    source_rows = _read_csv(DEFAULT_NEGATIVE_SOURCE_PATH)
    case_ids = [row["case_id"].strip() for row in source_rows]
    if not source_rows or any(not case_id for case_id in case_ids) or len(case_ids) != len(set(case_ids)):
        raise SystemExit("Negative case ids must be present and unique")
    fixture_nodeids = [row.get("fixture_nodeid", "").strip() for row in source_rows]
    if any(not nodeid or "::" not in nodeid for nodeid in fixture_nodeids):
        raise SystemExit("Every negative case must link to a pytest fixture_nodeid")
    missing_fixtures = [nodeid for nodeid in fixture_nodeids if not (PROJECT_ROOT / nodeid.split("::", 1)[0]).is_file()]
    if missing_fixtures:
        raise SystemExit(f"Negative fixture files do not exist: {', '.join(missing_fixtures)}")
    return {
        "schema_version": "1.1",
        "dataset_name": "vinfast_booking_negative_cases",
        "case_count": len(source_rows),
        "human_review_required": True,
        "provenance": {
            "source_file": "eval/golden/negative_cases.csv",
            "note": "Security and consistency regression cases; not operational seed data.",
        },
        "cases": [
            {
                "case_id": row["case_id"].strip(),
                "scenario": row["case"].strip(),
                "expected_outcome": row["expected"].strip(),
                "fixture_nodeid": row["fixture_nodeid"].strip(),
                "metric_groups": [group.strip() for group in row.get("metric_groups", "").split("|") if group.strip()],
                "review_status": "AUTOMATED_REGRESSION_NOT_HUMAN_REVIEWED",
            }
            for row in source_rows
        ],
    }


def main() -> int:
    args = parser().parse_args()
    data_dir = args.data_dir.resolve()
    output_dir = args.output_dir.resolve()
    rendered_files = {
        output_dir / "agent_cases.json": json.dumps(build(data_dir), ensure_ascii=False, indent=2) + "\n",
        output_dir / "negative_cases.json": json.dumps(build_negative_cases(data_dir), ensure_ascii=False, indent=2)
        + "\n",
    }
    if args.check:
        stale = [
            str(path)
            for path, rendered in rendered_files.items()
            if not path.is_file() or path.read_text(encoding="utf-8") != rendered
        ]
        if stale:
            raise SystemExit(f"Golden JSON is missing or stale: {', '.join(stale)}")
        print(f"Golden JSON files are current: {output_dir}")
        return 0
    output_dir.mkdir(parents=True, exist_ok=True)
    for path, rendered in rendered_files.items():
        path.write_text(rendered, encoding="utf-8")
        print(f"Built {path} with {len(json.loads(rendered)['cases'])} cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
