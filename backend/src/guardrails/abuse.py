from __future__ import annotations

import hashlib
import math
from collections.abc import Callable, Collection
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Any

from src.database import Database


@dataclass(frozen=True, slots=True)
class AbuseStatus:
    strike_count: int = 0
    banned: bool = False
    retry_after_seconds: int = 0


class AbuseTracker:
    """Persistent three-strike tracker that stores only hashed subjects."""

    def __init__(
        self,
        database: Database,
        *,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._database = database
        self._now = now

    def ensure_schema(self) -> None:
        with self._database.connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS guardrail_abuse_subjects (
                    subject_hash TEXT PRIMARY KEY,
                    strike_count INTEGER NOT NULL,
                    strike_window_started_at TEXT NOT NULL,
                    banned_until TEXT,
                    last_violation_code TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_guardrail_abuse_banned_until "
                "ON guardrail_abuse_subjects(banned_until)"
            )

    def check(self, subjects: Collection[str]) -> AbuseStatus:
        now = self._utc_now()
        statuses: list[AbuseStatus] = []
        with self._database.connect() as connection:
            for digest in self._subject_digests(subjects):
                row = connection.execute(
                    "SELECT strike_count,banned_until FROM guardrail_abuse_subjects WHERE subject_hash=?",
                    (digest,),
                ).fetchone()
                statuses.append(self._status_from_row(row, now))
        return self._merge_statuses(statuses)

    def record_violation(
        self,
        subjects: Collection[str],
        *,
        violation_code: str,
        max_strikes: int,
        strike_window_seconds: int,
        ban_seconds: int,
    ) -> AbuseStatus:
        now = self._utc_now()
        now_text = now.isoformat()
        statuses: list[AbuseStatus] = []
        with self._database.transaction(immediate=True) as connection:
            for digest in self._subject_digests(subjects):
                connection.execute(
                    """INSERT INTO guardrail_abuse_subjects(
                        subject_hash,strike_count,strike_window_started_at,banned_until,
                        last_violation_code,updated_at
                    ) VALUES(?,?,?,?,?,?) ON CONFLICT(subject_hash) DO NOTHING""",
                    (digest, 0, now_text, None, violation_code, now_text),
                )
                lock_suffix = " FOR UPDATE" if connection.dialect == "postgres" else ""
                row = connection.execute(
                    "SELECT strike_count,strike_window_started_at,banned_until "
                    "FROM guardrail_abuse_subjects WHERE subject_hash=?" + lock_suffix,
                    (digest,),
                ).fetchone()
                current = self._status_from_row(row, now)
                if current.banned:
                    statuses.append(current)
                    continue

                window_started = self._parse_datetime(row[1]) if row else now
                strike_count = int(row[0]) if row else 0
                if (now - window_started).total_seconds() >= strike_window_seconds:
                    window_started = now
                    strike_count = 0
                strike_count += 1
                banned_until = now + timedelta(seconds=ban_seconds) if strike_count >= max_strikes else None
                connection.execute(
                    """UPDATE guardrail_abuse_subjects
                    SET strike_count=?,strike_window_started_at=?,banned_until=?,
                        last_violation_code=?,updated_at=?
                    WHERE subject_hash=?""",
                    (
                        strike_count,
                        window_started.isoformat(),
                        banned_until.isoformat() if banned_until else None,
                        violation_code,
                        now_text,
                        digest,
                    ),
                )
                statuses.append(
                    AbuseStatus(
                        strike_count=strike_count,
                        banned=banned_until is not None,
                        retry_after_seconds=ban_seconds if banned_until else 0,
                    )
                )
        return self._merge_statuses(statuses)

    def clear(self) -> None:
        with self._database.transaction(immediate=True) as connection:
            connection.execute("DELETE FROM guardrail_abuse_subjects")

    @staticmethod
    def _subject_digests(subjects: Collection[str]) -> list[str]:
        return sorted(
            {
                hashlib.sha256(subject.encode("utf-8")).hexdigest()
                for subject in subjects
                if subject
            }
        )

    @staticmethod
    def _parse_datetime(value: Any) -> datetime:
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)

    def _utc_now(self) -> datetime:
        now = self._now()
        return now.astimezone(UTC) if now.tzinfo else now.replace(tzinfo=UTC)

    def _status_from_row(self, row: Any, now: datetime) -> AbuseStatus:
        if not row:
            return AbuseStatus()
        banned_until = self._parse_datetime(row[-1]) if row[-1] else None
        if banned_until and banned_until > now:
            return AbuseStatus(
                strike_count=int(row[0]),
                banned=True,
                retry_after_seconds=max(1, math.ceil((banned_until - now).total_seconds())),
            )
        return AbuseStatus(strike_count=int(row[0]))

    @staticmethod
    def _merge_statuses(statuses: Collection[AbuseStatus]) -> AbuseStatus:
        if not statuses:
            return AbuseStatus()
        return AbuseStatus(
            strike_count=max(status.strike_count for status in statuses),
            banned=any(status.banned for status in statuses),
            retry_after_seconds=max(status.retry_after_seconds for status in statuses),
        )


@lru_cache
def get_abuse_tracker() -> AbuseTracker:
    from src.dependencies import database

    tracker = AbuseTracker(database)
    tracker.ensure_schema()
    return tracker
