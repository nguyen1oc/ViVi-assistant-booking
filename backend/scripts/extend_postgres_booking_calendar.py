#!/usr/bin/env python3
"""Extend deterministic demo slots and staff assignments through a target date."""

from __future__ import annotations

import argparse
import hashlib
import sys
from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# ruff: noqa: E402 -- the script adds backend/ to sys.path before src imports.

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.bootstrap import initialize_database
from src.config import get_settings
from src.dependencies import database
from src.services.booking.common import iso

VIETNAM_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
DEFAULT_END_DATE = date(2026, 10, 31)
SLOT_WINDOWS = (
    (time(9, 0), time(10, 30)),
    (time(10, 30), time(12, 0)),
    (time(13, 30), time(15, 0)),
    (time(15, 0), time(16, 30)),
    (time(16, 30), time(18, 0)),
)
BLOCK_REASONS = ("vehicle_maintenance", "charging_required", "showroom_event")
BATCH_SIZE = 5_000


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        description="Extend test-drive slots and assignments without creating synthetic bookings."
    )
    command.add_argument("--end-date", type=date.fromisoformat, default=DEFAULT_END_DATE)
    command.add_argument("--apply", action="store_true", help="Commit generated rows. Default is dry-run.")
    return command


def _stable_id(prefix: str, *values: object) -> str:
    payload = "\x1f".join(str(value) for value in values)
    return f"{prefix}_{hashlib.sha256(payload.encode()).hexdigest()[:24]}"


def _block_reason(vehicle_id: str, local_date: date, window_index: int) -> str | None:
    payload = f"{vehicle_id}|{local_date.isoformat()}|{window_index}".encode()
    digest = hashlib.sha256(payload).digest()
    if int.from_bytes(digest[:4], "big") % 10:
        return None
    return BLOCK_REASONS[digest[4] % len(BLOCK_REASONS)]


def _chunks(rows: list[tuple], size: int = BATCH_SIZE):
    for offset in range(0, len(rows), size):
        yield rows[offset : offset + size]


def _local_date(value: str) -> date:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise SystemExit(f"Slot timestamp is missing a UTC offset: {value!r}")
    return parsed.astimezone(VIETNAM_TZ).date()


def _load_scope(connection):
    vehicles_by_showroom: dict[str, list[str]] = defaultdict(list)
    for row in connection.execute(
        "SELECT id,showroom_id FROM demo_vehicles ORDER BY showroom_id,id"
    ):
        vehicles_by_showroom[row["showroom_id"]].append(row["id"])

    staff_by_showroom: dict[str, list[str]] = defaultdict(list)
    for row in connection.execute(
        "SELECT id,showroom_id FROM sales_staff WHERE is_active=1 AND status='active' "
        "ORDER BY showroom_id,id"
    ):
        staff_by_showroom[row["showroom_id"]].append(row["id"])

    showroom_ids = [
        row["id"]
        for row in connection.execute("SELECT id FROM showrooms WHERE is_active=1 ORDER BY id")
    ]
    if len(showroom_ids) != 319:
        raise SystemExit(f"Expected 319 active showrooms; found {len(showroom_ids)}.")
    if sum(map(len, vehicles_by_showroom.values())) != 1_356:
        raise SystemExit("Expected 1,356 demo vehicles.")
    if sum(map(len, staff_by_showroom.values())) != 900:
        raise SystemExit("Expected 900 active staff.")
    missing_vehicles = [showroom_id for showroom_id in showroom_ids if not vehicles_by_showroom[showroom_id]]
    missing_staff = [showroom_id for showroom_id in showroom_ids if not staff_by_showroom[showroom_id]]
    if missing_vehicles or missing_staff:
        raise SystemExit(
            f"Every active showroom needs vehicles and staff; "
            f"missing vehicles={missing_vehicles}, missing staff={missing_staff}."
        )
    return showroom_ids, vehicles_by_showroom, staff_by_showroom


def _current_calendar_end(connection) -> tuple[date, int]:
    row = connection.execute(
        "SELECT start_at FROM test_drive_slots ORDER BY start_at DESC LIMIT 1"
    ).fetchone()
    if not row:
        raise SystemExit("Cannot extend an empty slot calendar.")
    last_date = _local_date(row["start_at"])
    count = connection.execute(
        "SELECT count(*) FROM test_drive_slots WHERE substr(start_at,1,10)=?",
        (last_date.isoformat(),),
    ).fetchone()[0]
    return last_date, count


def _rows_for_day(
    local_date: date,
    showroom_ids: list[str],
    vehicles_by_showroom: dict[str, list[str]],
    staff_by_showroom: dict[str, list[str]],
    generated_at: str,
) -> tuple[list[tuple], list[tuple], int]:
    slots: list[tuple] = []
    assignments: list[tuple] = []
    blocked_count = 0
    for showroom_id in showroom_ids:
        staff_ids = staff_by_showroom[showroom_id]
        assignment_index = 0
        for vehicle_id in vehicles_by_showroom[showroom_id]:
            for window_index, (start_time, end_time) in enumerate(SLOT_WINDOWS):
                start = datetime.combine(local_date, start_time, tzinfo=VIETNAM_TZ)
                end = datetime.combine(local_date, end_time, tzinfo=VIETNAM_TZ)
                slot_id = _stable_id("seed_slot", vehicle_id, start.isoformat(), end.isoformat())
                block_reason = _block_reason(vehicle_id, local_date, window_index)
                status = "blocked" if block_reason else "available"
                slots.append(
                    (
                        slot_id,
                        showroom_id,
                        vehicle_id,
                        start.isoformat(),
                        end.isoformat(),
                        status,
                        None,
                        None,
                        block_reason,
                        generated_at,
                        generated_at,
                    )
                )
                if block_reason:
                    blocked_count += 1
                    continue
                staff_id = staff_ids[assignment_index % len(staff_ids)]
                assignment_index += 1
                assignments.append(
                    (
                        _stable_id("seed_assignment", slot_id, staff_id),
                        slot_id,
                        staff_id,
                        "test_drive_consultant",
                        "assigned",
                        generated_at,
                        generated_at,
                    )
                )
    return slots, assignments, blocked_count


def extend(end_date: date, *, apply: bool) -> dict[str, object]:
    with database.connect() as connection:
        showroom_ids, vehicles_by_showroom, staff_by_showroom = _load_scope(connection)
        current_end, last_day_count = _current_calendar_end(connection)
        expected_daily_slots = sum(map(len, vehicles_by_showroom.values())) * len(SLOT_WINDOWS)
        if last_day_count != expected_daily_slots:
            raise SystemExit(
                f"Current last calendar day {current_end} is incomplete: "
                f"expected {expected_daily_slots} slots, found {last_day_count}."
            )
        start_date = current_end + timedelta(days=1)
        if start_date > end_date:
            return {
                "start_date": None,
                "end_date": current_end.isoformat(),
                "days_added": 0,
                "slots_added": 0,
                "assignments_added": 0,
                "blocked_slots_added": 0,
            }

        day_count = (end_date - start_date).days + 1
        generated_at = iso(datetime.now(UTC).replace(microsecond=0))
        summary: dict[str, object] = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days_added": day_count,
            "slots_added": 0,
            "assignments_added": 0,
            "blocked_slots_added": 0,
        }
        connection.execute("BEGIN")
        try:
            for day_offset in range(day_count):
                local_date = start_date + timedelta(days=day_offset)
                slots, assignments, blocked_count = _rows_for_day(
                    local_date,
                    showroom_ids,
                    vehicles_by_showroom,
                    staff_by_showroom,
                    generated_at,
                )
                summary["slots_added"] += len(slots)
                summary["assignments_added"] += len(assignments)
                summary["blocked_slots_added"] += blocked_count
                if not apply:
                    continue
                for batch in _chunks(slots):
                    connection.executemany(
                        "INSERT INTO test_drive_slots(id,showroom_id,demo_vehicle_id,start_at,end_at,status,"
                        "held_until,current_booking_id,block_reason,created_at,updated_at) "
                        "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                        batch,
                    )
                for batch in _chunks(assignments):
                    connection.executemany(
                        "INSERT INTO slot_sales_assignments(id,slot_id,sales_staff_id,assignment_role,status,"
                        "created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                        batch,
                    )

            if apply:
                final_count = connection.execute(
                    "SELECT count(*) FROM test_drive_slots WHERE substr(start_at,1,10) BETWEEN ? AND ?",
                    (start_date.isoformat(), end_date.isoformat()),
                ).fetchone()[0]
                expected_count = day_count * expected_daily_slots
                if final_count != expected_count:
                    raise SystemExit(
                        f"Extended calendar validation failed: expected {expected_count} new-date slots, "
                        f"found {final_count}."
                    )
                connection.commit()
            else:
                connection.rollback()
            return summary
        except BaseException:
            connection.rollback()
            raise


def main() -> int:
    args = parser().parse_args()
    settings = get_settings()
    initialize_database(database, settings)
    summary = extend(args.end_date, apply=args.apply)
    mode = "applied" if args.apply else "dry-run"
    print(f"PostgreSQL booking calendar extension {mode}: {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
