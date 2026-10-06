"""Provision internal portal users without committing default credentials."""

# ruff: noqa: E402 -- the script must add backend/ to sys.path before src imports.

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.bootstrap import initialize_database
from src.config import get_settings
from src.dependencies import database, internal_portal_service
from src.internal_portal import InternalPortalError, InternalRole


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description="Create a staff, showroom manager, or operations admin account.")
    command.add_argument("--username", required=True)
    command.add_argument("--display-name", required=True)
    command.add_argument("--role", required=True, choices=[role.value for role in InternalRole])
    command.add_argument("--staff-id")
    command.add_argument("--showroom-id", action="append", default=[])
    command.add_argument(
        "--password", help="Minimum 8 characters. Omit to enter it without exposing it in shell history."
    )
    return command


def main() -> int:
    args = parser().parse_args()
    password = args.password or getpass.getpass("Password: ")
    confirmation = password if args.password else getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")
    settings = get_settings()
    initialize_database(database, settings)
    try:
        user = internal_portal_service.create_user(
            username=args.username,
            password=password,
            display_name=args.display_name,
            role=args.role,
            staff_id=args.staff_id,
            showroom_ids=args.showroom_id,
        )
    except InternalPortalError as exc:
        raise SystemExit(f"{exc.code}: {exc}") from exc
    print(f"Created internal user {user['username']} ({user['role']}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
