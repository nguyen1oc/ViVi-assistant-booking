from __future__ import annotations

import csv
import io
import json
import os
import re
import threading
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .human_review_errors import HumanReviewError as InternalPortalError

HUMAN_REVIEW_COLUMNS = (
    "case_id",
    "reviewer_id",
    "task_success",
    "correctness_1_5",
    "relevance_1_5",
    "groundedness_1_5",
    "safety_1_5",
    "satisfaction_1_5",
    "forbidden_behaviors",
    "notes",
)
RATING_FIELDS = (
    "correctness_1_5",
    "relevance_1_5",
    "groundedness_1_5",
    "safety_1_5",
    "satisfaction_1_5",
)
FORBIDDEN_LABEL = re.compile(r"^[a-z0-9][a-z0-9_-]{0,79}$")
_WRITE_LOCK = threading.Lock()


def default_eval_root() -> Path:
    configured = os.getenv("EVAL_ROOT", "").strip()
    candidates = [
        Path(configured) if configured else None,
        Path("/app/eval"),
        Path(__file__).resolve().parents[3] / "eval",
        Path(__file__).resolve().parents[2] / "eval",
    ]
    for candidate in candidates:
        if candidate is not None and candidate.exists():
            return candidate.resolve()
    return (Path(__file__).resolve().parents[3] / "eval").resolve()


def _configured_path(name: str, default: Path, *, root: Path) -> Path:
    configured = os.getenv(name, "").strip()
    if not configured:
        return default
    path = Path(configured)
    return path if path.is_absolute() else root / path


def _read_json(path: Path, *, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise InternalPortalError(
            "EVALUATION_ARTIFACT_MISSING",
            f"Không tìm thấy {label}: {path}",
            status_code=503,
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InternalPortalError(
            "EVALUATION_ARTIFACT_INVALID",
            f"Không thể đọc {label}: {path}",
            status_code=503,
        ) from exc
    if not isinstance(payload, dict):
        raise InternalPortalError(
            "EVALUATION_ARTIFACT_INVALID",
            f"{label} phải là JSON object.",
            status_code=503,
        )
    return payload


def _spreadsheet_safe(value: str) -> str:
    stripped = value.lstrip()
    if stripped.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


class HumanReviewStore:
    def __init__(
        self,
        *,
        eval_root: Path | None = None,
        golden_path: Path | None = None,
        predictions_path: Path | None = None,
        evaluation_path: Path | None = None,
        reviews_path: Path | None = None,
        assignments_path: Path | None = None,
    ) -> None:
        root = (eval_root or default_eval_root()).resolve()
        self.golden_path = golden_path or _configured_path(
            "HUMAN_REVIEW_GOLDEN_PATH",
            root / "golden" / "agent_cases.json",
            root=root,
        )
        self.predictions_path = predictions_path or _configured_path(
            "HUMAN_REVIEW_PREDICTIONS_PATH",
            root / "results" / "agent-predictions.json",
            root=root,
        )
        self.evaluation_path = evaluation_path or _configured_path(
            "HUMAN_REVIEW_EVALUATION_PATH",
            root / "results" / "agent-evaluation.json",
            root=root,
        )
        self.reviews_path = reviews_path or _configured_path(
            "HUMAN_REVIEW_REVIEWS_PATH",
            root / "human" / "reviews.csv",
            root=root,
        )
        self.assignments_path = assignments_path or _configured_path(
            "HUMAN_REVIEW_ASSIGNMENTS_PATH",
            root / "human" / "assignments.csv",
            root=root,
        )

    def _artifacts(self) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        golden = _read_json(self.golden_path, label="golden dataset")
        predictions = _read_json(self.predictions_path, label="prediction artifact")
        evaluation = _read_json(self.evaluation_path, label="evaluation report")
        return golden, predictions, evaluation

    def _reviews(self) -> list[dict[str, str]]:
        if not self.reviews_path.is_file():
            return []
        try:
            with self.reviews_path.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
        except OSError as exc:
            raise InternalPortalError(
                "HUMAN_REVIEWS_UNAVAILABLE",
                "Không thể đọc dữ liệu human review.",
                status_code=503,
            ) from exc
        return [
            {column: str(row.get(column) or "") for column in HUMAN_REVIEW_COLUMNS}
            for row in rows
            if row.get("case_id") and row.get("reviewer_id")
        ]

    def _assignments(self) -> dict[str, set[str]] | None:
        """Return case assignments by reviewer, or None for legacy open queues."""
        if not self.assignments_path.is_file():
            return None
        try:
            with self.assignments_path.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
        except OSError as exc:
            raise InternalPortalError(
                "HUMAN_ASSIGNMENTS_UNAVAILABLE",
                "Không thể đọc phân công human review.",
                status_code=503,
            ) from exc
        if not rows or any(not row.get("case_id") or not row.get("reviewer_id") for row in rows):
            raise InternalPortalError(
                "HUMAN_ASSIGNMENTS_INVALID",
                "Phân công human review không hợp lệ.",
                status_code=503,
            )
        assignments: dict[str, set[str]] = defaultdict(set)
        for row in rows:
            assignments[str(row["reviewer_id"])].add(str(row["case_id"]))
        return assignments

    def _assert_assigned(self, case_id: str, reviewer_id: str) -> None:
        assignments = self._assignments()
        if assignments is not None and case_id not in assignments.get(reviewer_id, set()):
            raise InternalPortalError(
                "HUMAN_REVIEW_NOT_ASSIGNED",
                "Case này không được phân công cho reviewer hiện tại.",
                status_code=403,
            )

    @staticmethod
    def _active_cases(golden: dict[str, Any]) -> list[dict[str, Any]]:
        return [case for case in golden.get("cases", []) if case.get("evaluation_status") == "active"]

    @staticmethod
    def _first_user_input(case: dict[str, Any]) -> str:
        for turn in case.get("turns", []):
            if turn.get("role") == "user" and turn.get("content"):
                return str(turn["content"])
        for turn in case.get("turns", []):
            if turn.get("content"):
                return str(turn["content"])
        return "Không có câu người dùng."

    @staticmethod
    def _public_review(row: dict[str, str] | None) -> dict[str, Any] | None:
        if row is None:
            return None

        def optional_int(field: str) -> int | None:
            raw = row.get(field, "").strip()
            return int(raw) if raw else None

        result: dict[str, Any] = {
            "case_id": row["case_id"],
            "reviewer_id": row["reviewer_id"],
            "task_success": optional_int("task_success"),
            "forbidden_behaviors": [item for item in row["forbidden_behaviors"].split(";") if item],
            "notes": row["notes"],
        }
        result.update({field: optional_int(field) for field in RATING_FIELDS})
        return result

    @staticmethod
    def _is_complete_review(row: dict[str, str]) -> bool:
        return bool(row.get("task_success")) and all(bool(row.get(field)) for field in RATING_FIELDS)

    def list_queue(self, *, reviewer_id: str, reviewer_display_name: str) -> dict[str, Any]:
        golden, predictions, evaluation = self._artifacts()
        active_cases = self._active_cases(golden)
        global_case_count = len(active_cases)
        assignments = self._assignments()
        if assignments is not None:
            assigned_ids = assignments.get(reviewer_id, set())
            active_cases = [case for case in active_cases if str(case["case_id"]) in assigned_ids]
        prediction_by_id = {str(item.get("case_id")): item for item in predictions.get("cases", [])}
        evaluation_by_id = {str(item.get("case_id")): item for item in evaluation.get("cases", [])}
        reviews = self._reviews()
        reviews_by_case: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in reviews:
            reviews_by_case[row["case_id"]].append(row)

        items = []
        for case in active_cases:
            case_id = str(case["case_id"])
            case_reviews = reviews_by_case[case_id]
            complete_reviews = [row for row in case_reviews if self._is_complete_review(row)]
            task_values = {row["task_success"] for row in complete_reviews}
            my_review = next((row for row in case_reviews if row["reviewer_id"] == reviewer_id), None)
            expected = case.get("expected", {})
            prediction = prediction_by_id.get(case_id, {})
            automated = evaluation_by_id.get(case_id, {})
            items.append(
                {
                    "case_id": case_id,
                    "user_input": self._first_user_input(case),
                    "tags": case.get("tags", []),
                    "expected_intent": expected.get("intent"),
                    "expected_tool": expected.get("tool"),
                    "actual_intent": prediction.get("intent"),
                    "actual_tool": prediction.get("tool_calls", [{}])[-1].get("name")
                    if prediction.get("tool_calls")
                    else None,
                    "run_status": automated.get("run_status", "not_run"),
                    "review_count": len(complete_reviews),
                    "target_review_count": 2,
                    # Keep peer outcomes blind until this reviewer has submitted.
                    "has_disagreement": my_review is not None and len(task_values) > 1,
                    "my_review": self._public_review(my_review),
                }
            )

        reviewed_by_me = sum(item["my_review"] is not None for item in items)
        fully_reviewed = sum(item["review_count"] >= item["target_review_count"] for item in items)
        disagreements = sum(item["has_disagreement"] for item in items)
        return {
            "reviewer": {"id": reviewer_id, "display_name": reviewer_display_name},
            "artifact": {
                "dataset_name": golden.get("dataset_name"),
                "dataset_version": golden.get("dataset_version"),
                "prediction_generated_at": predictions.get("generated_at"),
                "model": predictions.get("model"),
            },
            "summary": {
                "total_cases": len(items),
                "reviewed_by_me": reviewed_by_me,
                "remaining_by_me": len(items) - reviewed_by_me,
                "fully_reviewed_cases": fully_reviewed,
                "total_reviews": sum(
                    self._is_complete_review(row) for rows in reviews_by_case.values() for row in rows
                ),
                "disagreement_cases": disagreements,
                "target_reviewers_per_case": 2,
                "global_active_cases": global_case_count,
                "assignment_mode": "fixed_pair" if assignments is not None else "open_queue",
            },
            "items": items,
        }

    def case_detail(self, case_id: str, *, reviewer_id: str) -> dict[str, Any]:
        self._assert_assigned(case_id, reviewer_id)
        golden, predictions, evaluation = self._artifacts()
        case = next(
            (item for item in self._active_cases(golden) if str(item.get("case_id")) == case_id),
            None,
        )
        if case is None:
            raise InternalPortalError(
                "EVALUATION_CASE_NOT_FOUND", "Không tìm thấy active evaluation case.", status_code=404
            )
        prediction = next(
            (item for item in predictions.get("cases", []) if str(item.get("case_id")) == case_id),
            None,
        )
        automated = next(
            (item for item in evaluation.get("cases", []) if str(item.get("case_id")) == case_id),
            None,
        )
        if prediction is None:
            raise InternalPortalError(
                "EVALUATION_PREDICTION_NOT_FOUND",
                "Case chưa có prediction để human review.",
                status_code=409,
            )
        case_reviews = [row for row in self._reviews() if row["case_id"] == case_id]
        my_review = next((row for row in case_reviews if row["reviewer_id"] == reviewer_id), None)
        return {
            "case_id": case_id,
            "golden": {
                "turns": case.get("turns", []),
                "ui_context": case.get("ui_context", {}),
                "expected": case.get("expected", {}),
                "tags": case.get("tags", []),
            },
            "prediction": {
                "intent": prediction.get("intent"),
                "skill": prediction.get("skill"),
                "response": prediction.get("response"),
                "tool_calls": prediction.get("tool_calls", []),
                "action_error": prediction.get("action_error"),
                "guardrail_blocked": prediction.get("guardrail_blocked"),
                "database_assertions": prediction.get("database_assertions", []),
                "forbidden_behavior_checks": prediction.get("forbidden_behavior_checks", {}),
                "groundedness_score": prediction.get("groundedness_score"),
                "hallucination_detected": prediction.get("hallucination_detected"),
                "judge_rationale": prediction.get("judge_rationale"),
                "turns": prediction.get("turns", []),
            },
            "automated_evaluation": automated,
            "review_count": sum(self._is_complete_review(row) for row in case_reviews),
            "my_review": self._public_review(my_review),
        }

    @staticmethod
    def _validated_row(case_id: str, reviewer_id: str, values: dict[str, Any]) -> dict[str, str]:
        task_success = int(values["task_success"])
        if task_success not in {0, 1}:
            raise InternalPortalError("INVALID_HUMAN_REVIEW", "Task success chỉ nhận 0 hoặc 1.")
        row = {
            "case_id": case_id,
            "reviewer_id": reviewer_id,
            "task_success": str(task_success),
        }
        for field in RATING_FIELDS:
            rating = int(values[field])
            if rating < 1 or rating > 5:
                raise InternalPortalError("INVALID_HUMAN_REVIEW", "Điểm human review phải nằm trong khoảng 1–5.")
            row[field] = str(rating)
        labels = list(dict.fromkeys(str(item).strip().casefold() for item in values.get("forbidden_behaviors", [])))
        if len(labels) > 30 or any(not FORBIDDEN_LABEL.fullmatch(item) for item in labels):
            raise InternalPortalError(
                "INVALID_FORBIDDEN_BEHAVIOR",
                "Nhãn hành vi cấm chỉ gồm chữ thường, số, dấu gạch ngang hoặc gạch dưới.",
            )
        notes = str(values.get("notes") or "").strip()
        if len(notes) > 2000:
            raise InternalPortalError("INVALID_HUMAN_REVIEW", "Ghi chú không được vượt quá 2.000 ký tự.")
        row["forbidden_behaviors"] = ";".join(labels)
        row["notes"] = _spreadsheet_safe(notes)
        return {column: row.get(column, "") for column in HUMAN_REVIEW_COLUMNS}

    def save_review(self, case_id: str, *, reviewer_id: str, values: dict[str, Any]) -> dict[str, Any]:
        self._assert_assigned(case_id, reviewer_id)
        golden, _, _ = self._artifacts()
        active_ids = [str(case["case_id"]) for case in self._active_cases(golden)]
        if case_id not in set(active_ids):
            raise InternalPortalError(
                "EVALUATION_CASE_NOT_FOUND", "Không tìm thấy active evaluation case.", status_code=404
            )
        row = self._validated_row(case_id, reviewer_id, values)
        with _WRITE_LOCK:
            rows = self._reviews()
            by_key = {(item["case_id"], item["reviewer_id"]): item for item in rows}
            by_key[(case_id, reviewer_id)] = row
            case_order = {active_case_id: index for index, active_case_id in enumerate(active_ids)}
            ordered = sorted(
                by_key.values(),
                key=lambda item: (case_order.get(item["case_id"], len(case_order)), item["reviewer_id"]),
            )
            self.reviews_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.reviews_path.with_suffix(self.reviews_path.suffix + ".tmp")
            try:
                with temporary.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=HUMAN_REVIEW_COLUMNS)
                    writer.writeheader()
                    writer.writerows(ordered)
                temporary.replace(self.reviews_path)
            except OSError as exc:
                raise InternalPortalError(
                    "HUMAN_REVIEWS_NOT_WRITABLE",
                    "Không thể lưu human review; hãy kiểm tra quyền ghi thư mục eval/human.",
                    status_code=503,
                ) from exc
        return self._public_review(row) or {}

    def export_csv(self) -> str:
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=HUMAN_REVIEW_COLUMNS)
        writer.writeheader()
        writer.writerows(self._reviews())
        return output.getvalue()

    def review_counts(self) -> Counter[str]:
        return Counter(row["case_id"] for row in self._reviews())
