#!/usr/bin/env python3
"""Export the canonical PostgreSQL business state as the portable V5 CSV seed."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

# ruff: noqa: E402 -- the script adds backend/ to sys.path before src imports.

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.dependencies import database
from src.services.booking.importer import ImportService


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description="Export PostgreSQL into eval/data V5 seed CSVs.")
    command.add_argument("--output-dir", type=Path, required=True)
    return command


def _order_columns(columns: list[str]) -> list[str]:
    if "id" in columns:
        return ["id"]
    if {"user_id", "showroom_id"}.issubset(columns):
        return ["user_id", "showroom_id"]
    for candidate in ("booking_id", "action_id", "token_hash", "showroom_id"):
        if candidate in columns:
            return [candidate]
    return columns


def _write_csv(path: Path, columns: list[str], rows) -> int:
    temporary = path.with_suffix(path.suffix + ".tmp")
    count = 0
    with temporary.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(columns)
        for row in rows:
            writer.writerow(["" if row[column] is None else row[column] for column in columns])
            count += 1
    temporary.replace(path)
    return count


def _build_reports(output_dir: Path, counts: dict[str, int], generated_at: str) -> None:
    seed_dir = output_dir / "seed"

    def read(filename: str) -> list[dict[str, str]]:
        with (seed_dir / filename).open(encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))

    staff = read("11_sales_staff.csv")
    users = read("12_internal_users.csv")
    bookings = read("22_bookings.csv")
    showrooms = read("04_showrooms.csv")
    vehicles = read("10_demo_vehicles.csv")
    slots = read("20_test_drive_slots.csv")
    shifts = read("15_staff_shifts.csv")
    active_staff_by_showroom = Counter(
        row["showroom_id"] for row in staff if row["is_active"] == "1" and row["status"] == "active"
    )
    role_counts = Counter(row["role"] for row in users if row["is_active"] == "1")
    status_counts = Counter(row["status"] for row in bookings)
    staff_distribution = Counter(active_staff_by_showroom.values())
    staff_ids = {row["id"] for row in staff if row["is_active"] == "1" and row["status"] == "active"}
    staff_accounts = [row for row in users if row["role"] == "staff" and row["is_active"] == "1"]
    showroom_geography_count = sum(
        bool(row["province_id"] and row["ward_id"] and not row["district_id"])
        for row in showrooms
    )
    slot_dates = {row["start_at"][:10] for row in slots}
    shift_dates = {row["start_at"][:10] for row in shifts}

    metadata = {
        "dataset_version": "5.2-postgres-enriched-baseline",
        "source_of_truth": "PostgreSQL business snapshot",
        "generated_at": generated_at,
        "showroom_count": len(showrooms),
        "active_staff_count": len(staff_ids),
        "demo_vehicle_count": len(vehicles),
        "test_drive_slot_count": len(slots),
        "booking_count": len(bookings),
        "booking_calendar": {
            "start_date": min(slot_dates),
            "end_date": max(slot_dates),
            "calendar_days": len(slot_dates),
            "booking_advance_window_days": 30,
        },
        "active_account_counts": dict(sorted(role_counts.items())),
        "booking_status_counts": dict(sorted(status_counts.items())),
        "staff_per_showroom_distribution": {
            str(staff_count): showroom_count for staff_count, showroom_count in sorted(staff_distribution.items())
        },
        "reference_and_derived_counts": {
            "provinces": counts["provinces"],
            "districts": counts["districts"],
            "wards": counts["wards"],
            "showrooms_with_province_and_ward": showroom_geography_count,
            "showroom_source_metadata": counts["showroom_source_metadata"],
            "showroom_services": counts["showroom_services"],
            "showroom_operating_hours": counts["showroom_operating_hours"],
            "staff_shifts": counts["staff_shifts"],
            "vehicle_unavailability": counts["vehicle_unavailability"],
        },
        "runtime_state_excluded": [
            "LangGraph checkpoint tables",
            "internal_notifications",
            "zalo_processed_messages",
            "active internal_sessions rows",
        ],
    }
    (output_dir / "GENERATION_METADATA.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    checks = {
        "showrooms_319": len(showrooms) == 319,
        "active_staff_900": len(staff_ids) == 900,
        "staff_accounts_900": role_counts["staff"] == 900,
        "manager_accounts_319": role_counts["showroom_manager"] == 319,
        "operations_admin_accounts_1": role_counts["operations_admin"] == 1,
        "staff_accounts_reference_active_staff": all(row["staff_id"] in staff_ids for row in staff_accounts),
        "usernames_unique": len(users) == len({row["username"].casefold() for row in users}),
        "internal_sessions_seed_empty": counts["internal_sessions"] == 0,
        "official_provinces_34": counts["provinces"] == 34,
        "districts_empty_for_two_tier_model": counts["districts"] == 0,
        "official_wards_3321": counts["wards"] == 3_321,
        "showroom_geography_319": showroom_geography_count == 319,
        "showroom_source_metadata_319": counts["showroom_source_metadata"] == 319,
        "showroom_services_319": counts["showroom_services"] == 319,
        "showroom_operating_hours_2233": counts["showroom_operating_hours"] == 2_233,
        "booking_calendar_ends_2026_10_31": max(slot_dates) == "2026-10-31",
        "derived_staff_shifts_cover_calendar": (
            shift_dates == slot_dates and counts["staff_shifts"] == len(staff_ids) * len(slot_dates)
        ),
        "derived_vehicle_unavailability_present": counts["vehicle_unavailability"] > 0,
        "staff_unavailability_has_no_source_events": counts["staff_unavailability"] == 0,
        "vehicle_transfers_have_no_source_events": counts["vehicle_transfers"] == 0,
        "booking_reschedules_have_no_source_events": counts["booking_reschedules"] == 0,
        "zalo_identity_links_runtime_empty": counts["zalo_identity_links"] == 0,
        "internal_audit_events_runtime_empty": counts["internal_audit_events"] == 0,
    }
    report = {
        "validation": "PASS" if all(checks.values()) else "FAIL",
        "dataset_version": metadata["dataset_version"],
        "source_of_truth": metadata["source_of_truth"],
        "generated_at": generated_at,
        "counts": counts,
        "active_account_counts": dict(sorted(role_counts.items())),
        "booking_status_counts": dict(sorted(status_counts.items())),
        "staff_per_showroom_distribution": metadata["staff_per_showroom_distribution"],
        "checks": {name: {"pass": passed} for name, passed in checks.items()},
        "errors": [name for name, passed in checks.items() if not passed],
        "notes": [
            "The PostgreSQL Docker database is the source of truth for this business snapshot.",
            "Runtime sessions, in-web notification read state, Zalo polling offsets, and LangGraph checkpoints are intentionally not seeded.",
            "Province and ward codes follow Decision 19/2025/QD-TTg; districts stay empty because the current official model is two-tier.",
            "Operating hours, staff shifts, and vehicle unavailability are deterministic demo-operating rows derived from PostgreSQL slots and assignments, not claims about official physical-showroom hours.",
            "Service, delivery, and charging flags remain false when the booking application has no independently verified source for them.",
            "The seed calendar extends through 2026-10-31; the API independently limits search and hold operations to 30 days from request time.",
        ],
    }
    (output_dir / "VALIDATION_REPORT.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if not all(checks.values()):
        raise SystemExit(f"Exported snapshot failed validation: {', '.join(report['errors'])}")


def _csv_row_count(path: Path) -> int:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        return sum(1 for _ in reader)


def _write_package_indexes(output_dir: Path) -> None:
    manifest_path = output_dir / "FILE_MANIFEST.csv"
    checksum_path = output_dir / "CHECKSUMS.sha256"
    package_files = sorted(
        (
            path
            for path in output_dir.rglob("*")
            if path.is_file() and path not in {manifest_path, checksum_path}
        ),
        key=lambda path: path.relative_to(output_dir).as_posix().casefold(),
    )
    entries = [
        (
            path.relative_to(output_dir).as_posix(),
            _csv_row_count(path) if path.suffix.casefold() == ".csv" else "",
            path.stat().st_size,
        )
        for path in package_files
    ]

    manifest_size = 0
    for _ in range(10):
        temporary = manifest_path.with_suffix(".csv.tmp")
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(("file_path", "row_count", "bytes"))
            writer.writerows(entries)
            writer.writerow((manifest_path.name, "", manifest_size))
        actual_size = temporary.stat().st_size
        if actual_size == manifest_size:
            temporary.replace(manifest_path)
            break
        manifest_size = actual_size
    else:
        raise SystemExit("FILE_MANIFEST.csv size did not converge")

    indexed_files = sorted(
        (*package_files, manifest_path),
        key=lambda path: path.relative_to(output_dir).as_posix().casefold(),
    )
    with checksum_path.open("w", encoding="utf-8", newline="\n") as handle:
        for path in indexed_files:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            handle.write(f"{digest}  {path.relative_to(output_dir).as_posix()}\n")


def export(output_dir: Path) -> dict[str, int]:
    seed_dir = output_dir / "seed"
    seed_dir.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    with database.connect() as connection:
        for filename, (table, columns) in ImportService.V5_DATASET_FILES.items():
            order = ",".join(_order_columns(columns))
            selected = ",".join(columns)
            rows = [] if table == "internal_sessions" else connection.execute(
                f"SELECT {selected} FROM {table} ORDER BY {order}"
            ).fetchall()
            counts[table] = _write_csv(seed_dir / filename, columns, rows)
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    _build_reports(output_dir, counts, generated_at)
    _write_package_indexes(output_dir)
    return counts


def main() -> int:
    args = parser().parse_args()
    counts = export(args.output_dir.resolve())
    print(f"Exported PostgreSQL business baseline: {sum(counts.values())} rows across {len(counts)} tables")
    print(json.dumps(counts, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
