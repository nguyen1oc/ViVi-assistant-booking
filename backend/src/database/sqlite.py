from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from .errors import DatabaseIntegrityError
from .guard import QueryGuard
from .rows import to_db_row
from .schema import SCHEMA_SQL


class SQLiteCursor:
    def __init__(self, cursor: sqlite3.Cursor) -> None:
        self._cursor = cursor

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount

    def fetchone(self):
        return to_db_row(self._cursor.fetchone())

    def fetchall(self):
        return [to_db_row(row) for row in self._cursor.fetchall()]

    def __iter__(self):
        for row in self._cursor:
            yield to_db_row(row)


class SQLiteConnection:
    dialect = "sqlite"

    def __init__(self, connection: sqlite3.Connection, guard: QueryGuard) -> None:
        self._connection = connection
        self._guard = guard

    def execute(self, sql: str, params: Sequence[Any] | None = None) -> SQLiteCursor:
        self._guard.validate(sql, tuple(params or ()))
        try:
            return SQLiteCursor(self._connection.execute(sql, tuple(params or ())))
        except sqlite3.IntegrityError as exc:
            raise DatabaseIntegrityError(str(exc)) from exc

    def executemany(self, sql: str, params: Iterable[Sequence[Any]]) -> SQLiteCursor:
        rows = [tuple(row) for row in params]
        if rows:
            self._guard.validate(sql, rows[0], many=True)
        try:
            return SQLiteCursor(self._connection.executemany(sql, rows))
        except sqlite3.IntegrityError as exc:
            raise DatabaseIntegrityError(str(exc)) from exc

    def executescript(self, script: str) -> None:
        self._connection.executescript(script)

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()

    def close(self) -> None:
        self._connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


class SQLiteDatabase:
    def __init__(self, path: str | Path, *, guard: QueryGuard) -> None:
        self.path = str(path)
        self.guard = guard
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> SQLiteConnection:
        connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            connection.execute("PRAGMA journal_mode=WAL")
        except sqlite3.OperationalError:
            pass
        for pragma in ("PRAGMA synchronous=NORMAL", "PRAGMA busy_timeout=10000"):
            try:
                connection.execute(pragma)
            except sqlite3.OperationalError:
                pass
        return SQLiteConnection(connection, self.guard)

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript("PRAGMA foreign_keys = ON;\n" + SCHEMA_SQL)
            self._migrate_legacy_schema(connection)

    @staticmethod
    def _columns(connection: SQLiteConnection, table: str) -> set[str]:
        return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}

    def _migrate_legacy_schema(self, connection: SQLiteConnection) -> None:
        additions = {
            "vehicle_models": {
                "seat_count": "INTEGER",
                "test_drive_eligible": "INTEGER NOT NULL DEFAULT 1 CHECK(test_drive_eligible IN (0,1))",
            },
            "vehicle_variants": {"default_test_drive_minutes": "INTEGER"},
            "showrooms": {
                "province_id": "TEXT REFERENCES provinces(id)",
                "district_id": "TEXT REFERENCES districts(id)",
                "ward_id": "TEXT REFERENCES wards(id)",
                "normalized_address": "TEXT",
                "region": "TEXT",
                "map_visible": "INTEGER NOT NULL DEFAULT 1 CHECK(map_visible IN (0,1))",
            },
            "sales_staff": {
                "role": "TEXT NOT NULL DEFAULT 'sales_consultant'",
                "is_active": "INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1))",
            },
            "bookings": {
                "assigned_sales_staff_id": "TEXT REFERENCES sales_staff(id)",
                "no_show_at": "TEXT",
                "customer_note": "TEXT",
                "internal_note": "TEXT",
            },
            "notification_plans": {"zalo_enabled": "INTEGER NOT NULL DEFAULT 0"},
            "notification_jobs": {
                "max_attempts": "INTEGER NOT NULL DEFAULT 3",
                "last_attempt_at": "TEXT",
                "provider_name": "TEXT",
                "provider_status": "TEXT",
                "is_mock": "INTEGER NOT NULL DEFAULT 1 CHECK(is_mock IN (0,1))",
                "provider_response_json": "TEXT",
            },
            "otp_challenges": {"consumed_at": "TEXT"},
            "idempotency_records": {
                "request_hash": "TEXT",
                "status": "TEXT NOT NULL DEFAULT 'succeeded'",
                "resource_id": "TEXT",
                "error_code": "TEXT",
                "expires_at": "TEXT",
            },
            "vehicle_transfers": {
                "approved_by": "TEXT REFERENCES internal_users(id)",
                "completed_by": "TEXT REFERENCES internal_users(id)",
                "requested_at": "TEXT",
                "approved_at": "TEXT",
                "reason": "TEXT",
            },
            "zalo_identity_links": {
                "id": "TEXT",
                "person_id": "TEXT REFERENCES people(id)",
                "phone_hash": "TEXT",
                "zalo_user_id": "TEXT",
                "is_active": "INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1))",
            },
            "rate_limit_counters": {},
            "llm_budget_ledger": {},
        }
        for table, columns in additions.items():
            existing = self._columns(connection, table)
            for name, definition in columns.items():
                if name not in existing:
                    connection.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
