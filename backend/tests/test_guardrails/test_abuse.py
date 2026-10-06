from datetime import UTC, datetime, timedelta

from src.database import Database
from src.guardrails.abuse import AbuseTracker


def test_abuse_tracker_bans_on_third_strike_persists_and_never_stores_raw_subject(tmp_path):
    current = [datetime(2026, 8, 21, 8, 0, tzinfo=UTC)]
    database = Database(tmp_path / "abuse.db")
    database.initialize()
    tracker = AbuseTracker(database, now=lambda: current[0])
    subjects = ("ip:203.0.113.7", "thread:conversation:abc")

    first = tracker.record_violation(
        subjects,
        violation_code="PROMPT_INJECTION_OVERRIDE",
        max_strikes=3,
        strike_window_seconds=3600,
        ban_seconds=86400,
    )
    second = tracker.record_violation(
        subjects,
        violation_code="ABUSIVE_LANGUAGE",
        max_strikes=3,
        strike_window_seconds=3600,
        ban_seconds=86400,
    )
    third = tracker.record_violation(
        subjects,
        violation_code="ROLE_INJECTION",
        max_strikes=3,
        strike_window_seconds=3600,
        ban_seconds=86400,
    )

    assert first.strike_count == 1 and first.banned is False
    assert second.strike_count == 2 and second.banned is False
    assert third.strike_count == 3 and third.banned is True
    assert third.retry_after_seconds == 86400
    assert AbuseTracker(database, now=lambda: current[0]).check(subjects).banned is True
    with database.connect() as connection:
        stored = connection.execute(
            "SELECT subject_hash FROM guardrail_abuse_subjects"
        ).fetchall()
    assert len(stored) == 2
    assert all(row[0] not in subjects for row in stored)

    current[0] += timedelta(seconds=86401)
    assert tracker.check(subjects).banned is False


def test_abuse_tracker_resets_strikes_after_the_configured_window(tmp_path):
    current = [datetime(2026, 8, 21, 8, 0, tzinfo=UTC)]
    database = Database(tmp_path / "abuse-window.db")
    database.initialize()
    tracker = AbuseTracker(database, now=lambda: current[0])
    kwargs = {
        "violation_code": "ABUSIVE_LANGUAGE",
        "max_strikes": 3,
        "strike_window_seconds": 60,
        "ban_seconds": 3600,
    }

    assert tracker.record_violation(("ip:test",), **kwargs).strike_count == 1
    current[0] += timedelta(seconds=61)
    reset = tracker.record_violation(("ip:test",), **kwargs)

    assert reset.strike_count == 1
    assert reset.banned is False
