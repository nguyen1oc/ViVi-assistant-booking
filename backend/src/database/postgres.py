from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any, cast

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - exercised only when dependency is missing.
    psycopg = cast(Any, None)
    dict_row = cast(Any, None)

from .errors import DatabaseIntegrityError
from .guard import QueryGuard, translate_qmark_placeholders
from .rows import to_db_row
from .schema import SCHEMA_SQL


def _require_psycopg():
    if psycopg is None:
        raise RuntimeError("PostgreSQL DATABASE_URL requires psycopg. Install backend requirements first.")
    return psycopg


class PostgresCursor:
    def __init__(self, cursor) -> None:
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


class PostgresConnection:
    dialect = "postgres"

    def __init__(self, connection, guard: QueryGuard) -> None:
        self._connection = connection
        self._guard = guard

    def execute(self, sql: str, params: Sequence[Any] | None = None) -> PostgresCursor:
        values = tuple(params or ())
        self._guard.validate(sql, values)
        cursor = self._connection.cursor()
        try:
            cursor.execute(translate_qmark_placeholders(sql, "%s"), values)
        except _require_psycopg().IntegrityError as exc:
            raise DatabaseIntegrityError(str(exc)) from exc
        return PostgresCursor(cursor)

    def executemany(self, sql: str, params: Iterable[Sequence[Any]]) -> PostgresCursor:
        rows = [tuple(row) for row in params]
        if rows:
            self._guard.validate(sql, rows[0], many=True)
        cursor = self._connection.cursor()
        try:
            cursor.executemany(translate_qmark_placeholders(sql, "%s"), rows)
        except _require_psycopg().IntegrityError as exc:
            raise DatabaseIntegrityError(str(exc)) from exc
        return PostgresCursor(cursor)

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


class PostgresDatabase:
    def __init__(self, url: str, *, guard: QueryGuard) -> None:
        self.url = url
        self.guard = guard

    def connect(self) -> PostgresConnection:
        pg = _require_psycopg()
        connection = pg.connect(self.url, row_factory=dict_row, autocommit=True)
        return PostgresConnection(connection, self.guard)

    def initialize(self) -> None:
        with self.connect() as connection:
            for statement in _split_statements(SCHEMA_SQL):
                connection.execute(statement)
            self._migrate_existing_schema(connection)

    @staticmethod
    def _columns(connection: PostgresConnection, table: str) -> set[str]:
        rows = connection.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=?",
            (table,),
        )
        return {row[0] for row in rows}

    def _migrate_existing_schema(self, connection: PostgresConnection) -> None:
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
        }
        for table, columns in additions.items():
            existing = self._columns(connection, table)
            for name, definition in columns.items():
                if name not in existing:
                    connection.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")
        self._migrate_v5_constraints(connection)

    @staticmethod
    def _migrate_v5_constraints(connection: PostgresConnection) -> None:
        """Relax legacy-only constraints while preserving the existing API columns."""
        statements = (
            "ALTER TABLE vehicle_models ALTER COLUMN required_license_class DROP NOT NULL",
            "ALTER TABLE vehicle_models ALTER COLUMN license_requirement_note DROP NOT NULL",
            "ALTER TABLE bookings ALTER COLUMN hold_expires_at DROP NOT NULL",
            "ALTER TABLE vehicle_variants DROP CONSTRAINT IF EXISTS vehicle_variants_code_key",
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_vehicle_variants_model_code_unique ON vehicle_variants(model_id,code)",
            "ALTER TABLE bookings DROP CONSTRAINT IF EXISTS bookings_rescheduled_from_booking_id_fkey",
            "ALTER TABLE bookings ADD CONSTRAINT bookings_rescheduled_from_booking_id_fkey FOREIGN KEY(rescheduled_from_booking_id) REFERENCES bookings(id) ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED",
            "ALTER TABLE bookings DROP CONSTRAINT IF EXISTS bookings_replaced_by_booking_id_fkey",
            "ALTER TABLE bookings ADD CONSTRAINT bookings_replaced_by_booking_id_fkey FOREIGN KEY(replaced_by_booking_id) REFERENCES bookings(id) ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED",
            "ALTER TABLE booking_driver_details DROP CONSTRAINT IF EXISTS booking_driver_details_license_check_status_check",
            "ALTER TABLE booking_driver_details ADD CONSTRAINT booking_driver_details_license_check_status_check CHECK(license_check_status IN ('not_provided','declared','pending','pending_in_person','verified','rejected','declared_ineligible'))",
            "ALTER TABLE notification_jobs DROP CONSTRAINT IF EXISTS notification_jobs_status_check",
            "ALTER TABLE notification_jobs ADD CONSTRAINT notification_jobs_status_check CHECK(status IN ('pending','processing','retrying','sent','failed','cancelled'))",
            "ALTER TABLE vehicle_transfers DROP CONSTRAINT IF EXISTS vehicle_transfers_status_check",
            "ALTER TABLE vehicle_transfers ADD CONSTRAINT vehicle_transfers_status_check CHECK(status IN ('requested','approved','completed','cancelled'))",
            "ALTER TABLE vehicle_transfers ALTER COLUMN effective_at DROP NOT NULL",
            "ALTER TABLE vehicle_transfers ALTER COLUMN created_at DROP NOT NULL",
            "ALTER TABLE vehicle_transfers ALTER COLUMN updated_at DROP NOT NULL",
            "ALTER TABLE internal_users DROP CONSTRAINT IF EXISTS internal_users_role_staff_binding_check",
            "ALTER TABLE internal_users ADD CONSTRAINT internal_users_role_staff_binding_check CHECK((role='staff' AND staff_id IS NOT NULL) OR (role<>'staff' AND staff_id IS NULL)) NOT VALID",
            "ALTER TABLE internal_users VALIDATE CONSTRAINT internal_users_role_staff_binding_check",
            "UPDATE zalo_identity_links SET id='zalo_legacy_' || md5(phone) WHERE id IS NULL",
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_zalo_identity_links_id_unique ON zalo_identity_links(id)",
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_zalo_identity_links_phone_hash_unique ON zalo_identity_links(phone_hash) WHERE phone_hash IS NOT NULL",
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_zalo_identity_links_user_unique ON zalo_identity_links(zalo_user_id) WHERE zalo_user_id IS NOT NULL",
        )
        for statement in statements:
            connection.execute(statement)


def _split_statements(script: str) -> list[str]:
    statements: list[str] = []
    current: list[str] = []
    in_string = False
    index = 0
    while index < len(script):
        char = script[index]
        if char == "'":
            in_string = not in_string
        if char == ";" and not in_string:
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
        else:
            current.append(char)
        index += 1
    tail = "".join(current).strip()
    if tail:
        statements.append(tail)
    return statements

