"""Create or rotate a Human Review Portal account."""

# ruff: noqa: E402 -- the script must add backend/ to sys.path before src imports.

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.evaluation.human_review_auth import HumanReviewAuth
from src.evaluation.human_review_errors import HumanReviewError as InternalPortalError


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description="Create or rotate a standalone Human Review account.")
    command.add_argument("--username", required=True)
    command.add_argument("--display-name", required=True)
    command.add_argument("--password", help="Minimum 8 characters. Omit to enter it securely.")
    command.add_argument("--inactive", action="store_true")
    return command


def main() -> int:
    args = parser().parse_args()
    password = args.password or getpass.getpass("Reviewer password: ")
    confirmation = password if args.password else getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")
    try:
        reviewer = HumanReviewAuth().create_reviewer(
            username=args.username,
            display_name=args.display_name,
            password=password,
            is_active=not args.inactive,
        )
    except InternalPortalError as exc:
        raise SystemExit(f"{exc.code}: {exc}") from exc
    print(f"Saved Human Review account {reviewer.username} ({reviewer.display_name}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
