#!/usr/bin/env python3
"""Enrich the PostgreSQL baseline with sourced and deterministically derived data."""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# ruff: noqa: E402 -- the script adds backend/ to sys.path before src imports.

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.bootstrap import initialize_database
from src.config import get_settings
from src.dependencies import database

ADMIN_REFERENCE = BACKEND_ROOT / "reference" / "vietnam_admin_units_2025.csv"
SHOWROOM_REFERENCE = (
    Path(os.getenv("EVAL_DATA_DIR", PROJECT_ROOT / "eval" / "data"))
    / "reference"
    / "showrooms_clean_319.csv"
)
LOCATOR_URL = "https://vinfastauto.com/vn_vi/tim-kiem-showroom-tram-sac"
SEED_TIMESTAMP = "2026-08-14T00:00:00+07:00"
VIETNAM_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        description="Fill sourced reference tables and derive operational seed rows from PostgreSQL."
    )
    command.add_argument("--admin-reference", type=Path, default=ADMIN_REFERENCE)
    command.add_argument("--showroom-reference", type=Path, default=SHOWROOM_REFERENCE)
    command.add_argument("--apply", action="store_true", help="Commit changes. Default is dry-run and rollback.")
    return command


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise SystemExit(f"Required reference file is missing: {path}")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _normalize(value: str) -> str:
    value = value.casefold().replace(chr(273), "d")
    value = "".join(
        character
        for character in unicodedata.normalize("NFD", value)
        if unicodedata.category(character) != "Mn"
    )
    return " ".join(re.findall(r"[a-z0-9]+", value))


def _bare_unit_name(value: str) -> str:
    normalized = _normalize(value)
    for prefix in (
        "thanh pho ",
        "tinh ",
        "phuong ",
        "xa ",
        "dac khu ",
        "thi tran ",
        "quan ",
        "huyen ",
        "tp ",
        "p ",
    ):
        if normalized.startswith(prefix):
            return normalized.removeprefix(prefix)
    return normalized


def _raw_key(value: str) -> str:
    return unicodedata.normalize("NFC", value.casefold()).strip()


def _stable_id(prefix: str, *values: object) -> str:
    payload = "\x1f".join(str(value) for value in values)
    return f"{prefix}_{hashlib.sha256(payload.encode()).hexdigest()[:24]}"


def _upsert(connection, table: str, primary_key: str, row: dict[str, object]) -> None:
    existing = connection.execute(
        f"SELECT 1 FROM {table} WHERE {primary_key}=?", (row[primary_key],)
    ).fetchone()
    if existing:
        updates = [column for column in row if column != primary_key]
        connection.execute(
            f"UPDATE {table} SET {','.join(f'{column}=?' for column in updates)} "
            f"WHERE {primary_key}=?",
            (*[row[column] for column in updates], row[primary_key]),
        )
        return
    columns = list(row)
    connection.execute(
        f"INSERT INTO {table}({','.join(columns)}) VALUES({','.join('?' for _ in columns)})",
        tuple(row[column] for column in columns),
    )


def _load_admin_reference(
    path: Path,
) -> tuple[dict[str, dict[str, str]], list[dict[str, str]]]:
    wards = _read_csv(path)
    provinces: dict[str, dict[str, str]] = {}
    for row in wards:
        provinces.setdefault(
            row["province_code"],
            {
                "code": row["province_code"],
                "name": row["province_name"],
                "unit_type": row["province_unit_type"],
                "effective_from": row["effective_from"],
            },
        )
    if len(provinces) != 34 or len(wards) != 3_321:
        raise SystemExit(
            f"Administrative reference must contain 34 provinces and 3,321 wards; "
            f"found {len(provinces)} and {len(wards)}."
        )
    if len({row["ward_code"] for row in wards}) != len(wards):
        raise SystemExit("Administrative reference contains duplicate ward codes.")
    return provinces, wards


def _load_showroom_reference(path: Path) -> dict[str, dict[str, str]]:
    rows = _read_csv(path)
    by_address: dict[str, dict[str, str]] = {}
    for row in rows:
        address_key = _raw_key(row["address"])
        if address_key in by_address:
            raise SystemExit(f"Showroom reference has a duplicate address: {row['address']}")
        by_address[address_key] = row
    if len(by_address) != 319:
        raise SystemExit(f"Showroom reference must contain 319 unique addresses; found {len(by_address)}.")
    return by_address


def _match_ward(
    showroom: dict[str, str],
    province_by_name: dict[str, dict[str, str]],
    wards_by_province_and_name: dict[str, dict[str, list[dict[str, str]]]],
) -> tuple[dict[str, str], dict[str, str]]:
    province = province_by_name.get(_normalize(showroom["province_city"]))
    if not province:
        raise SystemExit(
            f"Cannot map showroom {showroom['id']} province {showroom['province_city']!r}."
        )
    for component in reversed(showroom["address"].split(",")):
        candidates = wards_by_province_and_name[province["code"]].get(
            _bare_unit_name(component), []
        )
        if len(candidates) > 1:
            raw_component = _raw_key(component)
            exact = [candidate for candidate in candidates if _raw_key(candidate["ward_name"]) in raw_component]
            if len(exact) == 1:
                candidates = exact
        if len(candidates) == 1:
            return province, candidates[0]
        if len(candidates) > 1:
            names = ", ".join(candidate["ward_name"] for candidate in candidates)
            raise SystemExit(f"Ambiguous ward for showroom {showroom['id']}: {names}")
    raise SystemExit(
        f"Cannot map showroom {showroom['id']} to an official ward from {showroom['address']!r}."
    )


def _seed_administrative_units(
    connection,
    provinces: dict[str, dict[str, str]],
    wards: list[dict[str, str]],
) -> None:
    for province in provinces.values():
        _upsert(
            connection,
            "provinces",
            "id",
            {
                "id": f"province_{province['code']}",
                "code": province["code"],
                "name": province["name"],
                "normalized_name": _normalize(province["name"]),
                "unit_type": province["unit_type"],
                "effective_from": province["effective_from"],
                "effective_to": None,
                "is_active": 1,
                "created_at": SEED_TIMESTAMP,
                "updated_at": SEED_TIMESTAMP,
            },
        )
    for ward in wards:
        _upsert(
            connection,
            "wards",
            "id",
            {
                "id": f"ward_{ward['ward_code']}",
                "district_id": None,
                "province_id": f"province_{ward['province_code']}",
                "code": ward["ward_code"],
                "name": ward["ward_name"],
                "normalized_name": _normalize(ward["ward_name"]),
                "unit_type": ward["ward_unit_type"],
                "effective_from": ward["effective_from"],
                "effective_to": None,
                "is_active": 1,
                "created_at": SEED_TIMESTAMP,
                "updated_at": SEED_TIMESTAMP,
            },
        )


def _enrich_showrooms(
    connection,
    showroom_reference: dict[str, dict[str, str]],
    provinces: dict[str, dict[str, str]],
    wards: list[dict[str, str]],
) -> int:
    province_by_name = {_normalize(row["name"]): row for row in provinces.values()}
    wards_by_province_and_name: dict[str, dict[str, list[dict[str, str]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for ward in wards:
        wards_by_province_and_name[ward["province_code"]][_normalize(ward["ward_name"])].append(ward)

    db_showrooms = connection.execute("SELECT * FROM showrooms WHERE is_active=1 ORDER BY id").fetchall()
    if len(db_showrooms) != 319:
        raise SystemExit(f"Expected 319 active PostgreSQL showrooms; found {len(db_showrooms)}.")
    matched_reference_ids: set[str] = set()
    for db_showroom in db_showrooms:
        reference = showroom_reference.get(_raw_key(db_showroom["address"]))
        if not reference:
            raise SystemExit(
                f"PostgreSQL showroom {db_showroom['id']} has no reference address match: "
                f"{db_showroom['address']!r}"
            )
        if _raw_key(db_showroom["name"]) != _raw_key(reference["name"]):
            raise SystemExit(
                f"Showroom name mismatch at {db_showroom['address']!r}: "
                f"database={db_showroom['name']!r}, reference={reference['name']!r}"
            )
        matched_reference_ids.add(reference["id"])
        province, ward = _match_ward(reference, province_by_name, wards_by_province_and_name)
        connection.execute(
            "UPDATE showrooms SET province_id=?,district_id=NULL,ward_id=?,normalized_address=?,"
            "region=?,map_visible=?,updated_at=? WHERE id=?",
            (
                f"province_{province['code']}",
                f"ward_{ward['ward_code']}",
                _normalize(db_showroom["address"]),
                reference["region"],
                int(reference["map_visible"]),
                SEED_TIMESTAMP,
                db_showroom["id"],
            ),
        )
        _upsert(
            connection,
            "showroom_source_metadata",
            "showroom_id",
            {
                "showroom_id": db_showroom["id"],
                "public_source_id": reference["public_source_id"],
                "source_system": reference["source_id"] or "provided_showroom_snapshot",
                "source_url": LOCATOR_URL,
                "verification_status": reference["verification_status"],
                "quality_status": reference["quality_status"],
                "source_checked_at": reference["source_checked_at"] or None,
                "notes": (
                    "Imported from the supplied 319-showroom snapshot. The official locator is recorded "
                    "as the verification target; this individual row has not been independently reverified."
                ),
                "created_at": SEED_TIMESTAMP,
                "updated_at": SEED_TIMESTAMP,
            },
        )
    if len(matched_reference_ids) != len(showroom_reference):
        raise SystemExit("Not every showroom reference row mapped to PostgreSQL exactly once.")
    return len(db_showrooms)


def _manager_by_showroom(connection) -> dict[str, str]:
    rows = connection.execute(
        "SELECT scope.showroom_id,u.id FROM internal_users u "
        "JOIN internal_user_showrooms scope ON scope.user_id=u.id "
        "WHERE u.role='showroom_manager' AND u.is_active=1 ORDER BY u.created_at,u.id"
    ).fetchall()
    result: dict[str, str] = {}
    for row in rows:
        if row["showroom_id"] in result:
            raise SystemExit(f"Multiple active managers found for showroom {row['showroom_id']}.")
        result[row["showroom_id"]] = row["id"]
    if len(result) != 319:
        raise SystemExit(f"Expected one manager for each of 319 showrooms; found {len(result)}.")
    return result


def _seed_services(connection) -> int:
    vehicle_showrooms = {
        row["showroom_id"]
        for row in connection.execute(
            "SELECT showroom_id FROM demo_vehicles WHERE is_active=1 GROUP BY showroom_id"
        ).fetchall()
    }
    slot_showrooms = {
        row["showroom_id"]
        for row in connection.execute("SELECT showroom_id FROM test_drive_slots GROUP BY showroom_id").fetchall()
    }
    showrooms = connection.execute("SELECT id FROM showrooms WHERE is_active=1 ORDER BY id").fetchall()
    for showroom in showrooms:
        _upsert(
            connection,
            "showroom_services",
            "showroom_id",
            {
                "showroom_id": showroom["id"],
                "test_drive_enabled": int(
                    showroom["id"] in vehicle_showrooms and showroom["id"] in slot_showrooms
                ),
                "service_enabled": 0,
                "delivery_enabled": 0,
                "charging_enabled": 0,
                "created_at": SEED_TIMESTAMP,
                "updated_at": SEED_TIMESTAMP,
            },
        )
    return len(showrooms)


def _parse_local(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise SystemExit(f"Seed timestamp is missing a UTC offset: {value!r}")
    return parsed.astimezone(VIETNAM_TZ)


def _seed_operating_hours(connection) -> int:
    windows: dict[tuple[str, int], tuple[datetime, datetime]] = {}
    for row in connection.execute(
        "SELECT showroom_id,start_at,end_at FROM test_drive_slots ORDER BY showroom_id,start_at"
    ):
        start = _parse_local(row["start_at"])
        end = _parse_local(row["end_at"])
        key = (row["showroom_id"], start.weekday())
        current = windows.get(key)
        windows[key] = (
            min(start, current[0]) if current else start,
            max(end, current[1]) if current else end,
        )
    if len(windows) != 319 * 7:
        raise SystemExit(f"Expected seven slot windows for 319 showrooms; found {len(windows)}.")
    for (showroom_id, weekday), (start, end) in windows.items():
        _upsert(
            connection,
            "showroom_operating_hours",
            "id",
            {
                "id": _stable_id("seed_hours", showroom_id, weekday),
                "showroom_id": showroom_id,
                "day_of_week": weekday,
                "open_time": start.strftime("%H:%M"),
                "close_time": end.strftime("%H:%M"),
                "is_closed": 0,
                "created_at": SEED_TIMESTAMP,
                "updated_at": SEED_TIMESTAMP,
            },
        )
    return len(windows)


def _seed_staff_shifts(connection, managers: dict[str, str]) -> int:
    windows: dict[tuple[str, str, str], tuple[datetime, datetime]] = {}
    for row in connection.execute(
        "SELECT a.sales_staff_id,s.showroom_id,s.start_at,s.end_at "
        "FROM slot_sales_assignments a JOIN test_drive_slots s ON s.id=a.slot_id "
        "WHERE a.status='assigned' ORDER BY a.sales_staff_id,s.start_at"
    ):
        start = _parse_local(row["start_at"])
        end = _parse_local(row["end_at"])
        key = (row["sales_staff_id"], row["showroom_id"], start.date().isoformat())
        current = windows.get(key)
        windows[key] = (
            min(start, current[0]) if current else start,
            max(end, current[1]) if current else end,
        )
    active_staff_ids = {
        row["id"]
        for row in connection.execute(
            "SELECT id FROM sales_staff WHERE is_active=1 AND status='active'"
        )
    }
    calendar_dates = {key[2] for key in windows}
    covered_staff_dates = {(key[0], key[2]) for key in windows}
    expected_staff_dates = {
        (staff_id, calendar_date)
        for staff_id in active_staff_ids
        for calendar_date in calendar_dates
    }
    if covered_staff_dates != expected_staff_dates or len(windows) != len(expected_staff_dates):
        missing = len(expected_staff_dates - covered_staff_dates)
        extra = len(covered_staff_dates - expected_staff_dates)
        raise SystemExit(
            f"Derived shifts must cover every active staff/calendar date pair; "
            f"expected {len(expected_staff_dates)}, found {len(windows)}, missing={missing}, extra={extra}."
        )
    connection.execute("DELETE FROM staff_shifts WHERE id LIKE ?", ("seed_shift_%",))
    for (staff_id, showroom_id, local_date), (start, end) in windows.items():
        shift_id = _stable_id("seed_shift", staff_id, showroom_id, local_date)
        connection.execute(
            "INSERT INTO staff_shifts(id,sales_staff_id,showroom_id,start_at,end_at,status,created_by,"
            "created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (
                shift_id,
                staff_id,
                showroom_id,
                start.isoformat(),
                end.isoformat(),
                "scheduled",
                managers[showroom_id],
                SEED_TIMESTAMP,
                SEED_TIMESTAMP,
            ),
        )
    return len(windows)


def _seed_vehicle_unavailability(connection, managers: dict[str, str]) -> int:
    blocked: dict[tuple[str, str, str], list[tuple[datetime, datetime]]] = defaultdict(list)
    for row in connection.execute(
        "SELECT demo_vehicle_id,showroom_id,start_at,end_at,block_reason FROM test_drive_slots "
        "WHERE status='blocked' ORDER BY demo_vehicle_id,start_at"
    ):
        reason = row["block_reason"] or "blocked_slot"
        blocked[(row["demo_vehicle_id"], row["showroom_id"], reason)].append(
            (_parse_local(row["start_at"]), _parse_local(row["end_at"]))
        )

    ranges: list[tuple[str, str, str, datetime, datetime]] = []
    for (vehicle_id, showroom_id, reason), periods in blocked.items():
        range_start, range_end = periods[0]
        for start, end in periods[1:]:
            if start <= range_end:
                range_end = max(range_end, end)
            else:
                ranges.append((vehicle_id, showroom_id, reason, range_start, range_end))
                range_start, range_end = start, end
        ranges.append((vehicle_id, showroom_id, reason, range_start, range_end))

    connection.execute(
        "DELETE FROM vehicle_unavailability WHERE id LIKE ?", ("seed_vehicle_unavailability_%",)
    )
    for vehicle_id, showroom_id, reason, start, end in ranges:
        record_id = _stable_id(
            "seed_vehicle_unavailability", vehicle_id, showroom_id, reason, start.isoformat(), end.isoformat()
        )
        connection.execute(
            "INSERT INTO vehicle_unavailability(id,demo_vehicle_id,showroom_id,start_at,end_at,reason,"
            "created_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (
                record_id,
                vehicle_id,
                showroom_id,
                start.isoformat(),
                end.isoformat(),
                f"seed-derived:{reason}",
                managers[showroom_id],
                SEED_TIMESTAMP,
                SEED_TIMESTAMP,
            ),
        )
    return len(ranges)


def _validate(
    connection,
    expected_staff_shifts: int,
    expected_vehicle_unavailability: int,
) -> dict[str, int]:
    counts = {
        "provinces": connection.execute("SELECT count(*) FROM provinces WHERE is_active=1").fetchone()[0],
        "districts": connection.execute("SELECT count(*) FROM districts").fetchone()[0],
        "wards": connection.execute("SELECT count(*) FROM wards WHERE is_active=1").fetchone()[0],
        "showrooms_with_geography": connection.execute(
            "SELECT count(*) FROM showrooms WHERE is_active=1 AND province_id IS NOT NULL "
            "AND ward_id IS NOT NULL AND district_id IS NULL"
        ).fetchone()[0],
        "showroom_source_metadata": connection.execute(
            "SELECT count(*) FROM showroom_source_metadata"
        ).fetchone()[0],
        "showroom_services": connection.execute("SELECT count(*) FROM showroom_services").fetchone()[0],
        "showroom_operating_hours": connection.execute(
            "SELECT count(*) FROM showroom_operating_hours"
        ).fetchone()[0],
        "staff_shifts": connection.execute(
            "SELECT count(*) FROM staff_shifts WHERE id LIKE ?", ("seed_shift_%",)
        ).fetchone()[0],
        "vehicle_unavailability": connection.execute(
            "SELECT count(*) FROM vehicle_unavailability WHERE id LIKE ?",
            ("seed_vehicle_unavailability_%",),
        ).fetchone()[0],
    }
    expected = {
        "provinces": 34,
        "districts": 0,
        "wards": 3_321,
        "showrooms_with_geography": 319,
        "showroom_source_metadata": 319,
        "showroom_services": 319,
        "showroom_operating_hours": 2_233,
        "staff_shifts": expected_staff_shifts,
        "vehicle_unavailability": expected_vehicle_unavailability,
    }
    if counts != expected:
        raise SystemExit(f"Enriched baseline counts are invalid: expected {expected}, found {counts}")
    return counts


def enrich(
    admin_reference: Path,
    showroom_reference: Path,
    *,
    apply: bool,
) -> dict[str, int]:
    provinces, wards = _load_admin_reference(admin_reference)
    showrooms = _load_showroom_reference(showroom_reference)
    with database.connect() as connection:
        connection.execute("BEGIN")
        try:
            _seed_administrative_units(connection, provinces, wards)
            _enrich_showrooms(connection, showrooms, provinces, wards)
            managers = _manager_by_showroom(connection)
            _seed_services(connection)
            _seed_operating_hours(connection)
            shift_count = _seed_staff_shifts(connection, managers)
            unavailable_count = _seed_vehicle_unavailability(connection, managers)
            counts = _validate(connection, shift_count, unavailable_count)
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
    settings = get_settings()
    initialize_database(database, settings)
    counts = enrich(
        args.admin_reference.resolve(),
        args.showroom_reference.resolve(),
        apply=args.apply,
    )
    mode = "applied" if args.apply else "dry-run rolled back"
    print(f"PostgreSQL reference enrichment {mode}: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
