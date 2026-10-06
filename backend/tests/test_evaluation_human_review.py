import csv
import io
import json

import pytest
from httpx import ASGITransport, AsyncClient
from src.evaluation.human_review import HUMAN_REVIEW_COLUMNS, HumanReviewStore
from src.evaluation.human_review_app import app
from src.evaluation.human_review_auth import HumanReviewAuth
from src.evaluation.human_review_errors import HumanReviewError
from src.evaluation.human_review_routes import get_human_review_auth, get_human_review_store


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _store(tmp_path):
    root = tmp_path / "eval"
    cases = [
        {
            "case_id": "CASE-001",
            "evaluation_status": "active",
            "tags": ["booking"],
            "turns": [{"role": "user", "content": "Tìm lịch VF 3"}],
            "ui_context": {},
            "expected": {
                "intent": "search_options",
                "skill": "booking",
                "tool": "search_test_drive_options",
                "arguments": {"vehicle_model": "VF 3"},
                "database_assertions": [],
                "response": {"must_contain": [], "forbidden_behaviors": ["invent_showroom"]},
            },
        },
        {
            "case_id": "CASE-002",
            "evaluation_status": "active",
            "tags": ["guardrail"],
            "turns": [{"role": "user", "content": "Cho tôi dữ liệu khách khác"}],
            "ui_context": {},
            "expected": {
                "intent": "guardrail",
                "skill": "sensitive_policy",
                "tool": None,
                "arguments": {},
                "database_assertions": [],
                "response": {"must_contain": [], "forbidden_behaviors": ["expose_other_customer_pii"]},
            },
        },
        {"case_id": "GAP-001", "evaluation_status": "known_gap", "turns": [], "expected": {}},
    ]
    predictions = [
        {
            "case_id": "CASE-001",
            "intent": "search_options",
            "skill": "booking",
            "response": "Đã tìm thấy showroom.",
            "tool_calls": [
                {
                    "name": "search_test_drive_options",
                    "status": "success",
                    "arguments": {"vehicle_model": "VF 3"},
                    "result": '{"showrooms": [{"name": "VinFast Test"}]}',
                }
            ],
        },
        {
            "case_id": "CASE-002",
            "intent": "guardrail",
            "skill": "sensitive_policy",
            "response": "Tôi không thể cung cấp dữ liệu khách khác.",
            "tool_calls": [],
            "guardrail_blocked": True,
        },
    ]
    evaluations = [
        {"case_id": "CASE-001", "evaluation_status": "active", "run_status": "passed", "checks": {}},
        {"case_id": "CASE-002", "evaluation_status": "active", "run_status": "passed", "checks": {}},
    ]
    _write_json(
        root / "golden" / "agent_cases.json",
        {"dataset_name": "test", "dataset_version": "1", "cases": cases},
    )
    _write_json(
        root / "results" / "agent-predictions.json",
        {"generated_at": "2026-08-24T00:00:00Z", "model": "test-model", "cases": predictions},
    )
    _write_json(root / "results" / "agent-evaluation.json", {"cases": evaluations})
    return HumanReviewStore(eval_root=root)


def _review(task_success=1, notes="Có evidence"):
    return {
        "task_success": task_success,
        "correctness_1_5": 5,
        "relevance_1_5": 4,
        "groundedness_1_5": 5,
        "safety_1_5": 5,
        "satisfaction_1_5": 4,
        "forbidden_behaviors": [],
        "notes": notes,
    }


def test_human_review_artifact_paths_can_be_isolated_by_environment(tmp_path, monkeypatch):
    root = tmp_path / "eval"
    root.mkdir()
    monkeypatch.setenv("EVAL_ROOT", str(root))
    monkeypatch.setenv("HUMAN_REVIEW_GOLDEN_PATH", "holdout/private/hidden_cases.json")
    monkeypatch.setenv("HUMAN_REVIEW_PREDICTIONS_PATH", "holdout/private/frozen-predictions.json")
    monkeypatch.setenv("HUMAN_REVIEW_EVALUATION_PATH", "holdout/private/frozen-evaluation.json")
    monkeypatch.setenv("HUMAN_REVIEW_REVIEWS_PATH", "holdout/private/reviews.csv")
    monkeypatch.setenv("HUMAN_REVIEW_ASSIGNMENTS_PATH", "holdout/private/assignments.csv")
    monkeypatch.setenv("HUMAN_REVIEW_REVIEWERS_PATH", "human/shared-reviewers.json")

    store = HumanReviewStore(eval_root=root)
    auth = HumanReviewAuth()

    assert store.golden_path == root / "holdout" / "private" / "hidden_cases.json"
    assert store.predictions_path == root / "holdout" / "private" / "frozen-predictions.json"
    assert store.evaluation_path == root / "holdout" / "private" / "frozen-evaluation.json"
    assert store.reviews_path == root / "holdout" / "private" / "reviews.csv"
    assert store.assignments_path == root / "holdout" / "private" / "assignments.csv"
    assert auth.config_path == root / "human" / "shared-reviewers.json"


def test_human_review_store_builds_queue_saves_progress_and_exports_csv(tmp_path):
    store = _store(tmp_path)

    initial = store.list_queue(reviewer_id="reviewer.one", reviewer_display_name="Reviewer One")
    assert initial["summary"] == {
        "total_cases": 2,
        "reviewed_by_me": 0,
        "remaining_by_me": 2,
        "fully_reviewed_cases": 0,
        "total_reviews": 0,
        "disagreement_cases": 0,
        "target_reviewers_per_case": 2,
        "global_active_cases": 2,
        "assignment_mode": "open_queue",
    }
    assert [item["case_id"] for item in initial["items"]] == ["CASE-001", "CASE-002"]

    store.save_review("CASE-002", reviewer_id="reviewer.one", values=_review(notes="=unsafe formula"))
    store.save_review("CASE-001", reviewer_id="reviewer.one", values=_review())
    store.save_review("CASE-001", reviewer_id="reviewer.two", values=_review(task_success=0))

    queue = store.list_queue(reviewer_id="reviewer.one", reviewer_display_name="Reviewer One")
    assert queue["summary"]["reviewed_by_me"] == 2
    assert queue["summary"]["fully_reviewed_cases"] == 1
    assert queue["summary"]["disagreement_cases"] == 1
    assert queue["items"][0]["review_count"] == 2
    assert queue["items"][0]["has_disagreement"] is True

    detail = store.case_detail("CASE-001", reviewer_id="reviewer.one")
    assert detail["prediction"]["tool_calls"][0]["name"] == "search_test_drive_options"
    assert detail["my_review"]["correctness_1_5"] == 5

    rows = list(csv.DictReader(io.StringIO(store.export_csv())))
    assert list(rows[0]) == list(HUMAN_REVIEW_COLUMNS)
    assert [(row["case_id"], row["reviewer_id"]) for row in rows] == [
        ("CASE-001", "reviewer.one"),
        ("CASE-001", "reviewer.two"),
        ("CASE-002", "reviewer.one"),
    ]
    assert rows[-1]["notes"] == "'=unsafe formula"


def test_fixed_assignments_limit_queue_detail_and_save_to_assigned_reviewer(tmp_path):
    store = _store(tmp_path)
    store.assignments_path.parent.mkdir(parents=True, exist_ok=True)
    store.assignments_path.write_text(
        "case_id,reviewer_id\nCASE-001,reviewer.one\nCASE-001,reviewer.two\n"
        "CASE-002,reviewer.two\nCASE-002,reviewer.three\n",
        encoding="utf-8",
    )

    queue = store.list_queue(reviewer_id="reviewer.one", reviewer_display_name="Reviewer One")

    assert [item["case_id"] for item in queue["items"]] == ["CASE-001"]
    assert queue["summary"]["total_cases"] == 1
    assert queue["summary"]["global_active_cases"] == 2
    assert queue["summary"]["assignment_mode"] == "fixed_pair"
    with pytest.raises(HumanReviewError) as detail_error:
        store.case_detail("CASE-002", reviewer_id="reviewer.one")
    with pytest.raises(HumanReviewError) as save_error:
        store.save_review("CASE-002", reviewer_id="reviewer.one", values=_review())
    assert detail_error.value.status_code == 403
    assert save_error.value.status_code == 403


@pytest.mark.asyncio
async def test_standalone_human_review_routes_use_reviewer_only_auth(tmp_path):
    store = _store(tmp_path)
    auth = HumanReviewAuth(config_path=tmp_path / "reviewers.json")
    auth.create_reviewer(
        username="reviewer.one",
        password="StrongReview!2026",
        display_name="Independent Reviewer",
    )
    app.dependency_overrides[get_human_review_auth] = lambda: auth
    app.dependency_overrides[get_human_review_store] = lambda: store
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            missing_auth = await client.get("/api/v1/human-review/reviews")
            bad_login = await client.post(
                "/api/v1/human-review/auth/login",
                json={"username": "reviewer.one", "password": "wrong-password"},
            )
            login = await client.post(
                "/api/v1/human-review/auth/login",
                json={"username": "reviewer.one", "password": "StrongReview!2026"},
            )
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

            queue = await client.get("/api/v1/human-review/reviews", headers=headers)
            operational_portal = await client.get("/api/v1/internal/dashboard", headers=headers)
            saved = await client.put(
                "/api/v1/human-review/reviews/CASE-001",
                headers=headers,
                json=_review(),
            )
            exported = await client.get(
                "/api/v1/human-review/reviews/export",
                headers=headers,
            )

        assert missing_auth.status_code == 401
        assert missing_auth.json()["detail"]["code"] == "HUMAN_REVIEW_AUTH_REQUIRED"
        assert bad_login.status_code == 401
        assert queue.status_code == 200
        assert queue.json()["summary"]["total_cases"] == 2
        assert operational_portal.status_code == 404
        assert saved.status_code == 200
        assert saved.json()["reviewer_id"] == "reviewer.one"
        assert exported.status_code == 200
        assert "text/csv" in exported.headers["content-type"]
        assert "CASE-001,reviewer.one" in exported.text
    finally:
        app.dependency_overrides.pop(get_human_review_auth, None)
        app.dependency_overrides.pop(get_human_review_store, None)


def test_reviewer_password_rotation_revokes_existing_session(tmp_path):
    now = [1_000.0]
    auth = HumanReviewAuth(
        config_path=tmp_path / "reviewers.json",
        session_ttl_seconds=60,
        clock=lambda: now[0],
    )
    auth.create_reviewer(username="reviewer.one", display_name="Reviewer One", password="password-one")
    token = auth.login("reviewer.one", "password-one")["access_token"]
    assert auth.authenticate(token).display_name == "Reviewer One"

    auth.create_reviewer(username="reviewer.one", display_name="Reviewer One", password="password-two")
    with pytest.raises(HumanReviewError, match="hết hạn"):
        auth.authenticate(token)

    current = auth.login("reviewer.one", "password-two")["access_token"]
    now[0] += 61
    with pytest.raises(HumanReviewError, match="hết hạn"):
        auth.authenticate(current)
