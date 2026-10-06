from pathlib import Path

import pytest
from src.database import Database
from src.internal_portal import InternalPrincipal, InternalRole
from src.internal_portal.service import InternalPortalService
from src.services.booking import BookingService
from src.services.zalo_bot import ZaloOtpSender, normalize_phone

PROJECT_ROOT = Path(__file__).resolve().parents[3]
V5_DATASET_ROOT = PROJECT_ROOT / "eval" / "data"


@pytest.fixture(scope="module")
def v5_database(tmp_path_factory):
    if not (V5_DATASET_ROOT / "seed" / "32_internal_audit_events.csv").exists():
        pytest.skip("V5 incoming dataset is not present in this checkout.")
    database = Database(tmp_path_factory.mktemp("v5-database") / "v5.db", validate_schema=False)
    database.initialize()
    result = BookingService(database).import_eval_dataset_from_dir(V5_DATASET_ROOT)
    return database, result


def test_v5_import_loads_all_tables_atomically(v5_database):
    database, result = v5_database

    assert result["dataset_version"] == "v5"
    assert result["total_rows"] == sum(result["imported"].values())
    assert result["missing_expected_files"] == []
    assert len(result["imported"]) == 32
    with database.connect() as connection:
        assert connection.execute("SELECT count(*) FROM showrooms").fetchone()[0] == 319
        assert connection.execute("SELECT count(*) FROM provinces").fetchone()[0] == 34
        assert connection.execute("SELECT count(*) FROM districts").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM wards").fetchone()[0] == 3_321
        assert connection.execute(
            "SELECT count(*) FROM showrooms WHERE province_id IS NOT NULL AND ward_id IS NOT NULL "
            "AND district_id IS NULL"
        ).fetchone()[0] == 319
        assert connection.execute("SELECT count(*) FROM showroom_source_metadata").fetchone()[0] == 319
        assert connection.execute("SELECT count(*) FROM showroom_services").fetchone()[0] == 319
        assert connection.execute("SELECT count(*) FROM showroom_operating_hours").fetchone()[0] == 2_233
        assert connection.execute("SELECT count(*) FROM sales_staff").fetchone()[0] == 900
        assert connection.execute("SELECT count(*) FROM staff_shifts").fetchone()[0] == 76_500
        assert connection.execute("SELECT count(*) FROM vehicle_unavailability").fetchone()[0] == 56_131
        assert connection.execute("SELECT count(*) FROM staff_unavailability").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM vehicle_transfers").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM test_drive_slots").fetchone()[0] == 576_300
        assert connection.execute("SELECT count(*) FROM slot_sales_assignments").fetchone()[0] == 519_015
        assert connection.execute(
            "SELECT max(substr(start_at,1,10)) FROM test_drive_slots"
        ).fetchone()[0] == "2026-10-31"
        assert connection.execute("SELECT count(*) FROM bookings").fetchone()[0] == 9_369
        assert connection.execute("SELECT count(*) FROM booking_reschedules").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM zalo_identity_links").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM internal_audit_events").fetchone()[0] == 0
        assert connection.execute("SELECT count(DISTINCT full_name) FROM sales_staff").fetchone()[0] == 860
        assert connection.execute("SELECT count(*) FROM internal_users").fetchone()[0] == 1_220
        assert connection.execute(
            "SELECT count(*) FROM (SELECT showroom_id FROM sales_staff GROUP BY showroom_id HAVING count(*)=2)"
        ).fetchone()[0] == 78
        assert connection.execute("SELECT count(*) FROM people").fetchone()[0] == 11_976
        assert connection.execute("SELECT count(DISTINCT full_name) FROM people").fetchone()[0] == 6_376
        assert {
            row["status"]: row["total"]
            for row in connection.execute("SELECT status,count(*) total FROM bookings GROUP BY status")
        } == {
            "cancelled": 1_215,
            "completed": 1_192,
            "confirmed": 4_831,
            "held": 941,
            "no_show": 1_190,
        }
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_v5_seed_is_usable_by_internal_portal_and_zalo(v5_database):
    database, _ = v5_database
    with database.connect() as connection:
        operations_admin = connection.execute(
            "SELECT * FROM internal_users WHERE role='operations_admin' AND is_active=1 LIMIT 1"
        ).fetchone()
        person = connection.execute("SELECT id,phone FROM people WHERE phone IS NOT NULL LIMIT 1").fetchone()
    with database.transaction(immediate=True) as connection:
        connection.execute(
            "INSERT INTO zalo_identity_links(id,person_id,phone,chat_id,is_active,linked_at) "
            "VALUES(?,?,?,?,?,?)",
            (
                "zalo_v5_import_test",
                person["id"],
                normalize_phone(person["phone"]),
                "chat_v5_import_test",
                1,
                "2026-01-01T00:00:00Z",
            ),
        )

    principal = InternalPrincipal(
        operations_admin["id"],
        operations_admin["username"],
        operations_admin["display_name"],
        InternalRole.OPERATIONS_ADMIN,
        operations_admin["staff_id"],
        (),
    )
    dashboard = InternalPortalService(database).dashboard(principal)

    assert sum(dashboard["booking_counts"].values()) == 9_369
    assert ZaloOtpSender(database, object()).is_linked(person["phone"])


@pytest.mark.parametrize(
    ("username", "expected_role"),
    [
        ("admin.check", InternalRole.OPERATIONS_ADMIN),
        ("thanglongtayho.check", InternalRole.SHOWROOM_MANAGER),
        ("tuan.thanglongtayho", InternalRole.STAFF),
    ],
)
def test_v5_seeded_internal_accounts_can_log_in(v5_database, username, expected_role):
    database, _ = v5_database
    result = InternalPortalService(database).login(username, "1234512345")

    assert result["user"]["username"] == username
    assert result["user"]["role"] == expected_role.value
