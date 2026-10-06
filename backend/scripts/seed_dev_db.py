from __future__ import annotations

import csv
import os
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

# ruff: noqa: E402 -- the script adds backend/ to sys.path before src imports.

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.config import get_settings
from src.database import Database
from src.services.booking import BookingService

RESET_ORDER = (
    "driver_chat_invitations",
    "test_drive_context_signals",
    "booking_profile_summaries",
    "user_profile_signals",
    "user_profile_identities",
    "user_profiles",
    "internal_audit_events",
    "internal_notifications",
    "vehicle_transfers",
    "vehicle_unavailability",
    "staff_unavailability",
    "staff_shifts",
    "internal_sessions",
    "internal_user_showrooms",
    "internal_users",
    "booking_access_sessions",
    "otp_challenges",
    "zalo_processed_messages",
    "zalo_identity_links",
    "notification_jobs",
    "notification_plans",
    "booking_events",
    "booking_reschedules",
    "booking_driver_details",
    "idempotency_records",
    "bookings",
    "slot_sales_assignments",
    "test_drive_slots",
    "demo_vehicles",
    "vehicle_variants",
    "vehicle_models",
    "sales_staff",
    "showroom_operating_hours",
    "showroom_services",
    "showroom_source_metadata",
    "showrooms",
    "wards",
    "districts",
    "provinces",
    "people",
)

SEED_CHECK_TABLES = ("vehicle_models", "showrooms", "sales_staff", "demo_vehicles", "test_drive_slots", "bookings")


def _iso(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _seed_showrooms_from_csv(path: Path, now_str: str, limit: int = 8) -> list[tuple] | None:
    if not path.exists():
        return None
    rows = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            rows.append(
                (
                    row["id"],
                    row["code"],
                    row["name"],
                    row["address"],
                    float(row["latitude"]),
                    float(row["longitude"]),
                    row.get("phone") or None,
                    row.get("email") or None,
                    row.get("timezone") or "Asia/Ho_Chi_Minh",
                    0 if str(row.get("is_active", "1")).lower() in {"0", "false", "no"} else 1,
                    row.get("created_at") or now_str,
                    row.get("updated_at") or now_str,
                )
            )
            if len(rows) >= limit:
                break
    return rows or None


def _ensure_all_demo_vehicles(connection) -> None:
    now_str = _iso(datetime.now(UTC))
    showrooms = connection.execute("SELECT id FROM showrooms WHERE is_active=1").fetchall()
    variants = connection.execute("SELECT id, model_id FROM vehicle_variants WHERE is_active=1").fetchall()
    for s in showrooms:
        s_id = s["id"]
        for v in variants:
            v_id = v["id"]
            existing = connection.execute(
                "SELECT 1 FROM demo_vehicles WHERE showroom_id=? AND variant_id=? LIMIT 1",
                (s_id, v_id),
            ).fetchone()
            if not existing:
                dv_id = f"dv_auto_{s_id}_{v_id}"
                asset_code = f"SR{s_id}-DV-{v_id[:10]}"
                vin = f"VIN{abs(hash(dv_id)) % 1000000000:09d}2026EV"
                is_pg = getattr(connection, "dialect", "") == "postgres"
                insert_prefix = "INSERT INTO" if is_pg else "INSERT OR IGNORE INTO"
                conflict_sql = " ON CONFLICT (id) DO NOTHING" if is_pg else ""
                connection.execute(
                    f"{insert_prefix} demo_vehicles(id,showroom_id,variant_id,asset_code,vin,plate_number,operational_status,battery_soc,minimum_booking_soc,charging_status,is_active,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?){conflict_sql}",
                    (dv_id, s_id, v_id, asset_code, vin, "30M-999.99", "available", 95, 35, "not_charging", 1, now_str, now_str),
                )


def _extend_mock_slots(database: Database) -> int:
    """Extend the legacy fixture with slots through October 31, 2026.

    Slots are generated day by day through 2026-10-31 with realistic availability:
    - ~70% available
    - ~20% booked (Đã có lịch)
    - ~10% held (Đang được giữ)
    """
    raw_target = os.getenv("MOCK_SLOT_END_DATE", "2026-10-31").strip()
    if not raw_target:
        return 0
    try:
        target_date = date.fromisoformat(raw_target)
    except ValueError as exc:
        raise ValueError("MOCK_SLOT_END_DATE must use YYYY-MM-DD format.") from exc

    now_str = _iso(datetime.now(UTC))
    with database.transaction(immediate=True) as connection:
        _ensure_all_demo_vehicles(connection)
        latest_row = connection.execute("SELECT MAX(substr(start_at,1,10)) AS latest FROM test_drive_slots").fetchone()
        latest_raw = latest_row["latest"] if latest_row else None
        if not latest_raw:
            return 0
        latest_date = date.fromisoformat(latest_raw)
        if target_date <= latest_date:
            return 0

        source_slots = connection.execute(
            "SELECT id,showroom_id,demo_vehicle_id,start_at,end_at FROM test_drive_slots "
            "WHERE substr(start_at,1,10)=? ORDER BY id",
            (latest_raw,),
        ).fetchall()
        if not source_slots:
            return 0

        inserted = 0
        day = latest_date + timedelta(days=1)
        import hashlib

        while day <= target_date:
            day_prefix = day.isoformat()
            rows = []
            for slot in source_slots:
                # Deterministic random status allocation: 70% available, 20% booked, 10% held
                seed_key = f"{slot['id']}_{day_prefix}".encode()
                hash_val = int(hashlib.md5(seed_key).hexdigest(), 16) % 10
                if hash_val in (0, 1):
                    slot_status = "booked"
                elif hash_val == 2:
                    slot_status = "held"
                else:
                    slot_status = "available"

                rows.append(
                    (
                        f"mock_ext_{day:%Y%m%d}_{slot['id']}",
                        slot["showroom_id"],
                        slot["demo_vehicle_id"],
                        f"{day_prefix}{slot['start_at'][10:]}",
                        f"{day_prefix}{slot['end_at'][10:]}",
                        slot_status,
                        None,
                        None,
                        None,
                        now_str,
                        now_str,
                    )
                )
            connection.executemany(
                "INSERT INTO test_drive_slots("
                "id,showroom_id,demo_vehicle_id,start_at,end_at,status,held_until,current_booking_id,block_reason,created_at,updated_at"
                ") VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                rows,
            )
            inserted += len(rows)
            day += timedelta(days=1)
    return inserted


def seed_db() -> None:
    settings = get_settings()
    os.environ.setdefault("IMPORT_PROGRESS", "true")
    print(f"[seed] Connecting to database; eval data directory: {settings.eval_data_dir}", flush=True)
    database = Database(settings.database_url)
    database.initialize()
    service = BookingService(database)
    reset_requested = os.getenv("RESET_DEV_DB", "").lower() in {"1", "true", "yes"}

    with database.connect() as connection:
        existing_rows = sum(connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0] for table in SEED_CHECK_TABLES)
    if existing_rows and not reset_requested:
        print(
            "Database already contains booking data; seed skipped. "
            "Set RESET_DEV_DB=1 to replace dev fixtures."
        )
        return

    data_dir = Path(settings.eval_data_dir)
    if settings.auto_load_eval_data and data_dir.exists():
        if reset_requested:
            with database.transaction(immediate=True) as connection:
                print("[seed] Clearing existing tables before import...", flush=True)
                is_pg = getattr(connection, "dialect", "") == "postgres"
                if is_pg:
                    tables_str = ", ".join(RESET_ORDER)
                    connection.execute(f"TRUNCATE TABLE {tables_str} CASCADE")
                else:
                    for table in RESET_ORDER:
                        connection.execute(f"DELETE FROM {table}")
        result = service.import_eval_dataset_from_dir(data_dir)
        extended_slots = _extend_mock_slots(database)
        if extended_slots:
            print(f"[seed] Added {extended_slots:,} available mock slots through {os.environ.get('MOCK_SLOT_END_DATE', '2026-10-31')}.")
        print(f"Imported full eval dataset from {data_dir}: {result}")
        return

    now = datetime.now(UTC)
    now_str = _iso(now)

    # Cot cuoi la seat_count. Truoc day khong seed cot nay nen no NULL o moi mau xe,
    # keo theo email xac nhan khong noi duoc "xe may cho". So cho lay tu
    # src/services/site_catalog.py, la nguon so lieu xe trong repo.
    models = [
        ("model_vf3", "VF3", "VF 3", "Mini eSUV", "B1", "Yeu cau GPLX hang B1 tro len", 1, now_str, now_str, 4),
        ("model_vf5", "VF5", "VF 5", "A-SUV", "B1", "Yeu cau GPLX hang B1 tro len", 1, now_str, now_str, 5),
        ("model_vf6", "VF6", "VF 6", "B-SUV", "B1", "Yeu cau GPLX hang B1 tro len", 1, now_str, now_str, 5),
        ("model_vf7", "VF7", "VF 7", "C-SUV", "B1", "Yeu cau GPLX hang B1 tro len", 1, now_str, now_str, 5),
        ("model_vf8", "VF8", "VF 8", "D-SUV", "B1", "Yeu cau GPLX hang B1 tro len", 1, now_str, now_str, 5),
        ("model_vf9", "VF9", "VF 9", "E-SUV", "B1", "Yeu cau GPLX hang B1 tro len", 1, now_str, now_str, 7),
    ]

    variants = [
        ("var_vf3_eco", "model_vf3", "VF3-ECO", "Eco", 18.4, 210.0, 32.0, 1, now_str, now_str),
        ("var_vf5_plus", "model_vf5", "VF5-PLUS", "Plus", 37.23, 300.0, 100.0, 1, now_str, now_str),
        ("var_vf6_eco", "model_vf6", "VF6-ECO", "Eco", 59.6, 399.0, 130.0, 1, now_str, now_str),
        ("var_vf6_plus", "model_vf6", "VF6-PLUS", "Plus", 59.6, 381.0, 150.0, 1, now_str, now_str),
        ("var_vf7_base", "model_vf7", "VF7-BASE", "Base", 59.6, 375.0, 110.0, 1, now_str, now_str),
        ("var_vf7_plus", "model_vf7", "VF7-PLUS", "Plus", 75.3, 431.0, 260.0, 1, now_str, now_str),
        ("var_vf8_eco", "model_vf8", "VF8-ECO", "Eco", 87.7, 471.0, 260.0, 1, now_str, now_str),
        ("var_vf8_plus", "model_vf8", "VF8-PLUS", "Plus", 87.7, 447.0, 300.0, 1, now_str, now_str),
        ("var_vf9_eco", "model_vf9", "VF9-ECO", "Eco", 123.0, 580.0, 300.0, 1, now_str, now_str),
        ("var_vf9_plus", "model_vf9", "VF9-PLUS", "Plus", 123.0, 580.0, 300.0, 1, now_str, now_str),
    ]

    # Ten va dia chi showroom PHAI co dau tieng Viet. Ban truoc go khong dau nen
    # thu gui khach hien "VinFast Nguyen Van Cu" — doc ra nhu banh dich may.
    # Khong co file eval/data/03_showrooms.csv thi seed roi ve danh sach nay, tuc
    # la day chinh la thu khach nhin thay.
    #
    # CHUA SUA cap hanh chinh: dia chi van con cap quan/huyen (Long Bien, Cau Giay)
    # trong khi cap do da bo. Sua dung phai biet ten phuong moi, khong doan duoc.
    showrooms = [
        ("sr_hanoi", "SR-HANOI", "VinFast Nguyễn Văn Cừ", "3-5 Nguyễn Văn Cừ, Long Biên, Hà Nội", 21.045, 105.882, "024123456", "sr_hanoi@vinfast.vn", "Asia/Ho_Chi_Minh", 1, now_str, now_str),
        ("sr_hcm", "SR-HCM", "VinFast Landmark 81", "Vinhomes Central Park, Bình Thạnh, TP. Hồ Chí Minh", 10.795, 106.722, "028123456", "sr_hcm@vinfast.vn", "Asia/Ho_Chi_Minh", 1, now_str, now_str),
        ("sr_danang", "SR-DANANG", "VinFast Ngô Quyền", "910A Ngô Quyền, Sơn Trà, Đà Nẵng", 16.071, 108.231, "0236123456", "sr_danang@vinfast.vn", "Asia/Ho_Chi_Minh", 1, now_str, now_str),
        ("sr_smart_city", "SR-SMARTCITY", "VinFast Smart City", "Vinhomes Smart City, Nam Từ Liêm, Hà Nội", 21.004, 105.748, "024123457", "sr_smartcity@vinfast.vn", "Asia/Ho_Chi_Minh", 1, now_str, now_str),
        ("sr_royal_city", "SR-ROYAL", "VinFast Royal City", "72A Nguyễn Trãi, Thanh Xuân, Hà Nội", 21.003, 105.816, "024123458", "sr_royal@vinfast.vn", "Asia/Ho_Chi_Minh", 1, now_str, now_str),
        ("sr_mydinh", "SR-MYDINH", "VinFast Mỹ Đình", "8 Phạm Hùng, Cầu Giấy, Hà Nội", 21.028, 105.782, "024123459", "sr_mydinh@vinfast.vn", "Asia/Ho_Chi_Minh", 1, now_str, now_str),
        ("sr_ocean_park", "SR-OCEANPARK", "VinFast Ocean Park", "Vinhomes Ocean Park, Gia Lâm, Hà Nội", 20.989, 105.952, "024123460", "sr_oceanpark@vinfast.vn", "Asia/Ho_Chi_Minh", 1, now_str, now_str),
        ("sr_tayho", "SR-TAYHO", "VinFast Tây Hồ", "Võ Chí Công, Tây Hồ, Hà Nội", 21.072, 105.803, "024123461", "sr_tayho@vinfast.vn", "Asia/Ho_Chi_Minh", 1, now_str, now_str),
    ]
    showroom_csv = Path(settings.eval_data_dir) / "03_showrooms.csv"
    showrooms = _seed_showrooms_from_csv(showroom_csv, now_str) or showrooms

    staff = [
        (
            f"staff_{index + 1}",
            showroom[0],
            f"EMP-{index + 1:03d}",
            f"Sales Consultant {index + 1}",
            f"09000000{index + 1:02d}",
            f"sales{index + 1}@vinfast.vn",
            "sales_consultant",
            "active",
            1,
            now_str,
            now_str,
        )
        for index, showroom in enumerate(showrooms)
    ]

    demo_vehicles = []
    vehicle_idx = 1
    showroom_codes = [(showroom[0], f"SR{index + 1}") for index, showroom in enumerate(showrooms)]
    drive_variants = [
        ("var_vf3_eco", "VF3"),
        ("var_vf5_plus", "VF5"),
        ("var_vf6_plus", "VF6"),
        ("var_vf7_plus", "VF7"),
        ("var_vf8_plus", "VF8"),
        ("var_vf9_plus", "VF9"),
    ]
    for showroom_id, showroom_code in showroom_codes:
        for variant_id, variant_code in drive_variants:
            demo_vehicles.append(
                (
                    f"dv_{showroom_code.lower()}_{variant_code.lower()}",
                    showroom_id,
                    variant_id,
                    f"AST-{showroom_code}-{variant_code}",
                    f"VIN{showroom_code}DEMO{vehicle_idx:05d}",
                    f"{showroom_code}-DEMO-{vehicle_idx:02d}",
                    "available",
                    95.0,
                    15.0,
                    "not_charging",
                    1,
                    now_str,
                    now_str,
                )
            )
            vehicle_idx += 1

    slots = []
    slot_idx = 1
    base_date = now.date() + timedelta(days=1)
    for demo_vehicle in demo_vehicles:
        demo_vehicle_id, showroom_id = demo_vehicle[0], demo_vehicle[1]
        for day_offset in range(7):
            date = base_date + timedelta(days=day_offset)
            for start_time, end_time in (
                ("09:00:00", "10:00:00"),
                ("10:30:00", "11:30:00"),
                ("14:00:00", "15:00:00"),
                ("15:30:00", "16:30:00"),
            ):
                slots.append(
                    (
                        f"slot_{slot_idx}",
                        showroom_id,
                        demo_vehicle_id,
                        f"{date.isoformat()}T{start_time}+00:00",
                        f"{date.isoformat()}T{end_time}+00:00",
                        "available",
                        None,
                        None,
                        None,
                        now_str,
                        now_str,
                    )
                )
                slot_idx += 1

    with database.transaction(immediate=True) as connection:
        existing_rows = sum(
            connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            for table in ("vehicle_models", "showrooms", "sales_staff", "demo_vehicles", "test_drive_slots", "bookings")
        )
        reset_requested = os.getenv("RESET_DEV_DB", "").lower() in {"1", "true", "yes"}
        if existing_rows and not reset_requested:
            print(
                "Database already contains booking data; seed skipped. "
                "Set RESET_DEV_DB=1 to replace dev fixtures."
            )
            return

        for table in RESET_ORDER:
            connection.execute(f"DELETE FROM {table}")

        connection.executemany(
            "INSERT INTO vehicle_models(id,code,name,vehicle_type,required_license_class,license_requirement_note,is_active,created_at,updated_at,seat_count) VALUES(?,?,?,?,?,?,?,?,?,?)",
            models,
        )
        connection.executemany(
            "INSERT INTO vehicle_variants(id,model_id,code,name,battery_capacity_kwh,estimated_range_km,motor_power_kw,is_active,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            variants,
        )
        connection.executemany(
            "INSERT INTO showrooms(id,code,name,address,latitude,longitude,phone,email,timezone,is_active,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            showrooms,
        )
        connection.executemany(
            "INSERT INTO sales_staff(id,showroom_id,employee_code,full_name,phone,email,role,status,is_active,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            staff,
        )
        connection.executemany(
            "INSERT INTO demo_vehicles(id,showroom_id,variant_id,asset_code,vin,plate_number,operational_status,battery_soc,minimum_booking_soc,charging_status,is_active,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            demo_vehicles,
        )
        connection.executemany(
            "INSERT INTO test_drive_slots(id,showroom_id,demo_vehicle_id,start_at,end_at,status,held_until,current_booking_id,block_reason,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            slots,
        )

    if showroom_csv.exists():
        result = BookingService(database).import_showrooms_csv(showroom_csv.read_text(encoding="utf-8-sig"))
        print(f"Imported {result['imported']} showrooms from {showroom_csv}.")

    print(
        "Seeded database "
        f"{settings.database_url} with {len(models)} models, {len(variants)} variants, "
        f"{len(showrooms)} showrooms, {len(staff)} staff, {len(demo_vehicles)} vehicles, and {len(slots)} slots."
    )


if __name__ == "__main__":
    seed_db()
