"""Promote the current PostgreSQL database to the canonical 319-showroom baseline."""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

# ruff: noqa: E402 -- the script adds backend/ to sys.path before src imports.

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.bootstrap import initialize_database
from src.config import get_settings
from src.dependencies import database
from src.internal_portal.service import _password_digest


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        description="Merge rejected showroom records into their canonical showroom records."
    )
    command.add_argument(
        "--mapping-file",
        type=Path,
        default=Path(os.getenv("EVAL_DATA_DIR", BACKEND_ROOT.parent / "eval" / "data"))
        / "reference"
        / "rejected_showrooms_10.csv",
    )
    command.add_argument(
        "--password",
        help="Expected shared demo password. Required with --apply to verify every active account.",
    )
    command.add_argument("--apply", action="store_true", help="Commit the migration. Default is dry-run and rollback.")
    return command


def _read_mapping(path: Path) -> list[tuple[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise SystemExit(f"Mapping file is empty: {path}")
    canonical_names: dict[str, str] = {}
    for reference_name in ("showrooms_clean_319.csv", "showrooms_hanoi_demo_47.csv"):
        with (path.parent / reference_name).open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                canonical_names[row["id"]] = row["name"]
    return [(row["name"], canonical_names[row["kept_canonical_id"]]) for row in rows]


def _showroom_id_by_name(connection, name: str) -> str | None:
    matches = connection.execute(
        "SELECT id FROM showrooms WHERE lower(trim(name))=lower(trim(?))", (name,)
    ).fetchall()
    if len(matches) > 1:
        raise SystemExit(f"Showroom name is not unique in PostgreSQL: {name!r}")
    return matches[0]["id"] if matches else None


def _manager_by_showroom(connection, showroom_id: str):
    return connection.execute(
        "SELECT u.* FROM internal_users u JOIN internal_user_showrooms s ON s.user_id=u.id "
        "WHERE s.showroom_id=? AND u.role='showroom_manager' ORDER BY u.is_active DESC,u.created_at,u.id LIMIT 1",
        (showroom_id,),
    ).fetchone()


def _merge_manager(connection, rejected_id: str, canonical_id: str) -> None:
    rejected = _manager_by_showroom(connection, rejected_id)
    canonical = _manager_by_showroom(connection, canonical_id)
    if not rejected:
        return
    if not canonical:
        connection.execute(
            "UPDATE internal_user_showrooms SET showroom_id=? WHERE user_id=? AND showroom_id=?",
            (canonical_id, rejected["id"], rejected_id),
        )
        return

    connection.execute(
        "DELETE FROM internal_notifications n WHERE n.recipient_user_id=? AND EXISTS ("
        "SELECT 1 FROM internal_notifications keep WHERE keep.recipient_user_id=? "
        "AND keep.booking_id=n.booking_id AND keep.notification_type=n.notification_type)",
        (rejected["id"], canonical["id"]),
    )
    connection.execute(
        "UPDATE internal_notifications SET recipient_user_id=?,showroom_id=? WHERE recipient_user_id=?",
        (canonical["id"], canonical_id, rejected["id"]),
    )

    connection.execute(
        "UPDATE staff_shifts SET created_by=? WHERE created_by=?", (canonical["id"], rejected["id"])
    )
    connection.execute(
        "UPDATE staff_unavailability SET created_by=? WHERE created_by=?", (canonical["id"], rejected["id"])
    )
    connection.execute(
        "UPDATE vehicle_unavailability SET created_by=? WHERE created_by=?", (canonical["id"], rejected["id"])
    )
    for column in ("requested_by", "approved_by", "completed_by"):
        connection.execute(
            f"UPDATE vehicle_transfers SET {column}=? WHERE {column}=?", (canonical["id"], rejected["id"])
        )
    connection.execute(
        "UPDATE internal_audit_events SET actor_user_id=? WHERE actor_user_id=?",
        (canonical["id"], rejected["id"]),
    )
    connection.execute("DELETE FROM internal_users WHERE id=?", (rejected["id"],))


def _merge_showroom(connection, rejected_id: str, canonical_id: str) -> None:
    _merge_manager(connection, rejected_id, canonical_id)

    for table, column in (
        ("sales_staff", "showroom_id"),
        ("demo_vehicles", "showroom_id"),
        ("test_drive_slots", "showroom_id"),
        ("staff_shifts", "showroom_id"),
        ("staff_unavailability", "showroom_id"),
        ("vehicle_unavailability", "showroom_id"),
        ("internal_audit_events", "showroom_id"),
    ):
        connection.execute(f"UPDATE {table} SET {column}=? WHERE {column}=?", (canonical_id, rejected_id))
    for column in ("from_showroom_id", "to_showroom_id"):
        connection.execute(
            f"UPDATE vehicle_transfers SET {column}=? WHERE {column}=?", (canonical_id, rejected_id)
        )

    # A canonical manager may already have the same booking notification. Keep
    # that row and discard only the duplicate recipient/type notification.
    connection.execute(
        "UPDATE internal_notifications SET showroom_id=? WHERE showroom_id=?", (canonical_id, rejected_id)
    )

    # These tables describe the physical location itself. The canonical row is
    # authoritative, so rejected-location metadata is not merged.
    connection.execute("DELETE FROM showroom_operating_hours WHERE showroom_id=?", (rejected_id,))
    connection.execute("DELETE FROM showroom_services WHERE showroom_id=?", (rejected_id,))
    connection.execute("DELETE FROM showroom_source_metadata WHERE showroom_id=?", (rejected_id,))
    connection.execute("DELETE FROM internal_user_showrooms WHERE showroom_id=?", (rejected_id,))
    connection.execute("DELETE FROM showrooms WHERE id=?", (rejected_id,))


def _assert_baseline(connection, password: str | None) -> dict[str, int]:
    counts = {
        "showrooms": connection.execute("SELECT count(*) FROM showrooms WHERE is_active=1").fetchone()[0],
        "staff": connection.execute("SELECT count(*) FROM sales_staff WHERE is_active=1").fetchone()[0],
        "managers": connection.execute(
            "SELECT count(*) FROM internal_users WHERE role='showroom_manager' AND is_active=1"
        ).fetchone()[0],
        "staff_accounts": connection.execute(
            "SELECT count(*) FROM internal_users WHERE role='staff' AND is_active=1"
        ).fetchone()[0],
        "admins": connection.execute(
            "SELECT count(*) FROM internal_users WHERE role='operations_admin' AND is_active=1"
        ).fetchone()[0],
    }
    expected = {"showrooms": 319, "staff": 900, "managers": 319, "staff_accounts": 900, "admins": 1}
    if counts != expected:
        raise SystemExit(f"Baseline counts are not valid: expected {expected}, found {counts}")
    orphan_count = connection.execute(
        "SELECT count(*) FROM internal_users u LEFT JOIN sales_staff s ON s.id=u.staff_id "
        "WHERE u.role='staff' AND (s.id IS NULL OR s.is_active<>1 OR s.status<>'active')"
    ).fetchone()[0]
    if orphan_count:
        raise SystemExit(f"Found {orphan_count} staff accounts without active staff records.")
    if password is not None:
        failed = 0
        for row in connection.execute(
            "SELECT password_salt,password_hash FROM internal_users WHERE is_active=1"
        ).fetchall():
            if _password_digest(password, bytes.fromhex(row["password_salt"])) != row["password_hash"]:
                failed += 1
        if failed:
            raise SystemExit(f"Shared demo password does not match {failed} active accounts.")
    return counts


def migrate(mapping: list[tuple[str, str]], *, password: str | None, apply: bool) -> dict[str, int]:
    with database.connect() as connection:
        connection.execute("BEGIN")
        try:
            for rejected_name, canonical_name in mapping:
                rejected_id = _showroom_id_by_name(connection, rejected_name)
                canonical_id = _showroom_id_by_name(connection, canonical_name)
                if not canonical_id:
                    raise SystemExit(
                        "Showroom mapping cannot be applied: "
                        f"rejected={rejected_name!r}, canonical={canonical_name!r}"
                    )
                if not rejected_id:
                    continue
                _merge_showroom(connection, rejected_id, canonical_id)
            counts = _assert_baseline(connection, password)
            if apply:
                connection.commit()
            else:
                connection.rollback()
            return counts
        except BaseException:
            connection.rollback()
            raise


def main() -> int:
    args = parser().parse_args()
    if args.apply and not args.password:
        raise SystemExit("--password is required with --apply")
    settings = get_settings()
    initialize_database(database, settings)
    mapping = _read_mapping(args.mapping_file.resolve())
    counts = migrate(mapping, password=args.password, apply=args.apply)
    mode = "applied" if args.apply else "dry-run rolled back"
    print(f"PostgreSQL baseline migration {mode}: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
