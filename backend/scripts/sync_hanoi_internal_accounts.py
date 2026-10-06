"""Synchronize demo staff and internal portal accounts.

The script can provision either two staff per Hanoi showroom or every active
staff member in the system. Existing staff, booking, and assignment data is
left unchanged.
"""

# ruff: noqa: E402 -- the script must add backend/ to sys.path before src imports.

from __future__ import annotations

import argparse
import csv
import os
import re
import secrets
import sys
import unicodedata
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.bootstrap import initialize_database
from src.config import get_settings
from src.dependencies import database
from src.internal_portal.service import _password_digest
from src.services.booking.common import iso, new_id, utcnow

EXPECTED_SHOWROOMS = 47
STAFF_PER_SHOWROOM = 2


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        description="Create internal portal accounts for the selected showroom scope."
    )
    command.add_argument("--password", required=True, help="Password assigned to every synchronized account.")
    command.add_argument(
        "--scope",
        choices=("hanoi", "all"),
        default="hanoi",
        help="Use two staff per Hanoi showroom or every active staff member system-wide.",
    )
    command.add_argument(
        "--data-dir",
        type=Path,
        default=Path(os.getenv("EVAL_DATA_DIR", BACKEND_ROOT.parent / "eval" / "data")),
        help="Dataset directory containing reference/ and seed/.",
    )
    return command


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise SystemExit(f"Required dataset file is missing: {path}")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _current_showroom_id(public_source_id: str) -> str:
    match = re.fullmatch(r"VFVN_(\d+)", public_source_id.strip())
    if not match:
        raise SystemExit(f"Invalid public showroom id: {public_source_id!r}")
    return str(int(match.group(1)))


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.casefold().replace("đ", "d"))
    return "".join(character for character in normalized if character.isascii() and character.isalnum())


def _load_demo_scope(data_dir: Path) -> list[dict[str, str]]:
    hanoi_rows = _read_csv(data_dir / "reference" / "showrooms_hanoi_demo_47.csv")
    if len(hanoi_rows) != EXPECTED_SHOWROOMS:
        raise SystemExit(f"Expected {EXPECTED_SHOWROOMS} Hanoi showrooms, found {len(hanoi_rows)}.")

    scope_by_user: dict[str, str] = {}
    for row in _read_csv(data_dir / "seed" / "13_internal_user_showrooms.csv"):
        scope_by_user[row["user_id"]] = row["showroom_id"]
    manager_by_reference_id = {
        scope_by_user[row["id"]]: row["username"]
        for row in _read_csv(data_dir / "seed" / "12_internal_users.csv")
        if row["role"] == "showroom_manager" and row["id"] in scope_by_user
    }

    result = []
    for row in hanoi_rows:
        reference_id = row["id"]
        current_id = _current_showroom_id(row["public_source_id"])
        manager_username = manager_by_reference_id.get(current_id) or manager_by_reference_id.get(reference_id)
        if not manager_username or not manager_username.endswith(".check"):
            raise SystemExit(f"Manager username is missing for {reference_id}.")
        result.append(
            {
                "id": current_id,
                "name": row["name"],
                "manager_username": manager_username,
                "account_stem": manager_username.removesuffix(".check"),
            }
        )
    return result


def _load_all_scope(connection) -> list[dict[str, str]]:
    existing_managers = {
        row["showroom_id"]: row["username"]
        for row in connection.execute(
            "SELECT scope.showroom_id,u.username FROM internal_users u "
            "JOIN internal_user_showrooms scope ON scope.user_id=u.id "
            "WHERE u.role='showroom_manager' ORDER BY u.created_at,u.username"
        ).fetchall()
    }
    showrooms = connection.execute(
        "SELECT id,code,name FROM showrooms WHERE is_active=1 ORDER BY code,id"
    ).fetchall()
    used_usernames = {"admin.check"}
    reserved_existing = set(existing_managers.values())
    result = []
    for row in showrooms:
        existing_username = existing_managers.get(row["id"], "")
        if existing_username.endswith(".check") and existing_username not in used_usernames:
            manager_username = existing_username
            reserved_existing.discard(existing_username)
        else:
            stem = _slug(row["name"].removeprefix("VinFast ")) or f"showroom{_slug(row['code'])}"
            sequence = 1
            while True:
                suffix = "" if sequence == 1 else str(sequence)
                manager_username = f"{stem}{suffix}.check"
                if manager_username not in used_usernames and manager_username not in reserved_existing:
                    break
                sequence += 1
        used_usernames.add(manager_username)
        result.append(
            {
                "id": row["id"],
                "name": row["name"],
                "manager_username": manager_username,
                "account_stem": manager_username.removesuffix(".check"),
            }
        )
    return result


def _staff_rank(staff_id: str) -> tuple[int, str]:
    match = re.search(r"_(\d+)$", staff_id)
    return (int(match.group(1)) if match else 10_000, staff_id)


def _staff_username(full_name: str, account_stem: str, used: set[str]) -> str:
    given_name = _slug(full_name.split()[-1])
    if not given_name:
        raise SystemExit(f"Cannot generate a username for staff member {full_name!r}.")
    sequence = 1
    while True:
        prefix = given_name if sequence == 1 else f"{given_name}{sequence}"
        username = f"{prefix}.{account_stem}"
        if username not in used:
            used.add(username)
            return username
        sequence += 1


def _password_fields(password: str) -> tuple[str, str]:
    salt = secrets.token_bytes(16)
    return salt.hex(), _password_digest(password, salt)


def _upsert_user(
    connection,
    *,
    username: str,
    display_name: str,
    role: str,
    password: str,
    staff_id: str | None = None,
    showroom_id: str | None = None,
) -> str:
    existing = None
    if staff_id:
        existing = connection.execute("SELECT * FROM internal_users WHERE staff_id=?", (staff_id,)).fetchone()
    if not existing:
        existing = connection.execute("SELECT * FROM internal_users WHERE username=?", (username,)).fetchone()

    now = iso(utcnow())
    salt, digest = _password_fields(password)
    if existing:
        user_id = existing["id"]
        connection.execute(
            "UPDATE internal_users SET username=?,display_name=?,password_salt=?,password_hash=?,"
            "role=?,staff_id=?,is_active=1,updated_at=? WHERE id=?",
            (username, display_name, salt, digest, role, staff_id, now, user_id),
        )
    else:
        user_id = new_id("iuser")
        connection.execute(
            "INSERT INTO internal_users(id,username,display_name,password_salt,password_hash,role,staff_id,"
            "is_active,last_login_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (user_id, username, display_name, salt, digest, role, staff_id, 1, None, now, now),
        )

    connection.execute("DELETE FROM internal_user_showrooms WHERE user_id=?", (user_id,))
    if showroom_id:
        connection.execute(
            "INSERT INTO internal_user_showrooms(user_id,showroom_id,created_at) VALUES(?,?,?)",
            (user_id, showroom_id, now),
        )
    connection.execute(
        "UPDATE internal_sessions SET revoked_at=? WHERE user_id=? AND revoked_at IS NULL",
        (now, user_id),
    )
    return user_id


def synchronize(password: str, data_dir: Path, *, scope: str = "hanoi") -> dict[str, int]:
    if len(password) < 8:
        raise SystemExit("Password must contain at least 8 characters.")
    summary = {
        "showrooms": 0,
        "staff_accounts": 0,
        "manager_accounts": 0,
        "admin_accounts": 0,
    }
    with database.transaction(immediate=True) as connection:
        demo_showrooms = _load_demo_scope(data_dir) if scope == "hanoi" else _load_all_scope(connection)
        showroom_ids = {item["id"] for item in demo_showrooms}
        summary["showrooms"] = len(demo_showrooms)
        existing_showrooms = {
            row["id"]
            for row in connection.execute(
                f"SELECT id FROM showrooms WHERE id IN ({','.join('?' for _ in showroom_ids)}) AND is_active=1",
                tuple(sorted(showroom_ids)),
            ).fetchall()
        }
        missing = sorted(showroom_ids - existing_showrooms)
        if missing:
            raise SystemExit(f"Active Hanoi showrooms are missing from PostgreSQL: {', '.join(missing)}")

        kept_by_showroom: dict[str, list[dict]] = {}
        for showroom in demo_showrooms:
            staff_rows = sorted(
                (
                    dict(row)
                    for row in connection.execute(
                        "SELECT id,full_name FROM sales_staff "
                        "WHERE showroom_id=? AND status='active' AND is_active=1 ORDER BY id",
                        (showroom["id"],),
                    ).fetchall()
                ),
                key=lambda item: _staff_rank(item["id"]),
            )
            if len(staff_rows) < STAFF_PER_SHOWROOM:
                raise SystemExit(f"Showroom {showroom['id']} has fewer than two staff records.")
            kept_by_showroom[showroom["id"]] = (
                staff_rows if scope == "all" else staff_rows[:STAFF_PER_SHOWROOM]
            )

        admin = connection.execute(
            "SELECT * FROM internal_users WHERE role='operations_admin' ORDER BY is_active DESC,created_at LIMIT 1"
        ).fetchone()
        if admin and admin["username"] != "admin.check":
            connection.execute("UPDATE internal_users SET username=? WHERE id=?", ("admin.check", admin["id"]))
        _upsert_user(
            connection,
            username="admin.check",
            display_name="Admin tổng",
            role="operations_admin",
            password=password,
        )
        summary["admin_accounts"] = 1

        used_usernames = {"admin.check"}
        for showroom in demo_showrooms:
            manager_username = showroom["manager_username"]
            used_usernames.add(manager_username)
            _upsert_user(
                connection,
                username=manager_username,
                display_name=f"Quản lý {showroom['name'].removeprefix('VinFast ').strip()}",
                role="showroom_manager",
                password=password,
                showroom_id=showroom["id"],
            )
            summary["manager_accounts"] += 1

            existing_staff_usernames = {
                row["staff_id"]: row["username"]
                for row in connection.execute(
                    f"SELECT staff_id,username FROM internal_users WHERE staff_id IN "
                    f"({','.join('?' for _ in kept_by_showroom[showroom['id']])})",
                    tuple(staff["id"] for staff in kept_by_showroom[showroom["id"]]),
                ).fetchall()
            }
            for staff in kept_by_showroom[showroom["id"]]:
                expected_suffix = f".{showroom['account_stem']}"
                existing_username = existing_staff_usernames.get(staff["id"], "")
                username = (
                    existing_username
                    if existing_username.endswith(expected_suffix) and existing_username not in used_usernames
                    else _staff_username(staff["full_name"], showroom["account_stem"], used_usernames)
                )
                used_usernames.add(username)
                _upsert_user(
                    connection,
                    username=username,
                    display_name=staff["full_name"],
                    role="staff",
                    password=password,
                    staff_id=staff["id"],
                )
                summary["staff_accounts"] += 1

    return summary


def main() -> int:
    args = parser().parse_args()
    settings = get_settings()
    initialize_database(database, settings)
    summary = synchronize(args.password, args.data_dir.resolve(), scope=args.scope)
    print(
        f"Synchronized {args.scope} demo accounts: "
        f"{summary['showrooms']} showrooms, {summary['staff_accounts']} staff, "
        f"{summary['manager_accounts']} managers, {summary['admin_accounts']} admin."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
