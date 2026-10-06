import pytest
from src.database.sqlite import SQLiteConnection
from src.services.booking import BookingError
from src.services.booking.importer import ImportService


def test_v5_people_import_derives_missing_normalized_contacts(booking_service):
    row = {
        "phone": "090 123 4567",
        "email": "  Customer@Example.Test ",
        "normalized_phone": "",
        "normalized_email": "",
    }

    values = booking_service._row_values(
        row,
        ["normalized_phone", "normalized_email"],
        filename="19_people.csv",
        is_v5=True,
        v5_people_by_id={},
    )

    assert values == ("0901234567", "customer@example.test")


VALID_SHOWROOM_CSV = """code,name,address,latitude,longitude,phone,email,timezone,is_active
SR-NEW,Showroom New,123 Test Street,10.75,106.70,0900000000,new@example.com,Asia/Ho_Chi_Minh,1
"""


# test case of Chau + kiểm tra import showroom CSV hợp lệ tạo record mới
def test_import_showrooms_csv_success(booking_service, booking_db):
    result = booking_service.import_showrooms_csv(VALID_SHOWROOM_CSV)

    assert result == {"imported": 1}
    with booking_db.connect() as connection:
        showroom = connection.execute("SELECT * FROM showrooms WHERE code='SR-NEW'").fetchone()
    assert showroom["name"] == "Showroom New"
    assert showroom["is_active"] == 1


# test case of Chau + kiểm tra import lại showroom cùng code thực hiện upsert không tạo trùng
def test_import_showrooms_csv_upserts_existing_record(booking_service, booking_db):
    booking_service.import_showrooms_csv(VALID_SHOWROOM_CSV)
    updated_csv = VALID_SHOWROOM_CSV.replace("Showroom New", "Showroom Updated")

    booking_service.import_showrooms_csv(updated_csv)

    with booking_db.connect() as connection:
        rows = connection.execute("SELECT * FROM showrooms WHERE code='SR-NEW'").fetchall()
    assert len(rows) == 1
    assert rows[0]["name"] == "Showroom Updated"


# test case of Chau + kiểm tra từ chối showroom CSV thiếu header bắt buộc
def test_import_showrooms_csv_rejects_missing_header(booking_service):
    csv_text = "code,name,address,latitude\nSR-1,Test,Address,10.7\n"

    with pytest.raises(BookingError) as error:
        booking_service.import_showrooms_csv(csv_text)

    assert error.value.code == "INVALID_INPUT"


# test case of Chau + kiểm tra từ chối tọa độ showroom không phải số
def test_import_showrooms_csv_rejects_invalid_coordinates(booking_service):
    csv_text = VALID_SHOWROOM_CSV.replace("10.75", "not-a-number")

    with pytest.raises(BookingError) as error:
        booking_service.import_showrooms_csv(csv_text)

    assert error.value.code == "INVALID_INPUT"


# test case of Chau + kiểm tra dataset importer từ chối tên file không được hỗ trợ
def test_import_eval_dataset_rejects_unknown_file(booking_service):
    with pytest.raises(BookingError) as error:
        booking_service.import_eval_dataset({"malicious.csv": "id,name\n1,test\n"})

    assert error.value.code == "INVALID_INPUT"


def test_slot_timestamp_import_normalizes_to_explicit_utc():
    rows = [{"start_at": "2026-08-03T09:00:00+07:00", "end_at": "2026-08-03T10:30:00+07:00", "held_until": ""}]

    ImportService._normalize_slot_timestamps(rows, filename="06_test_drive_slots.csv")

    assert rows[0]["start_at"] == "2026-08-03T02:00:00+00:00"
    assert rows[0]["end_at"] == "2026-08-03T03:30:00+00:00"


def test_slot_timestamp_import_rejects_end_before_start():
    rows = [{"start_at": "2026-08-03T09:00:00+07:00", "end_at": "2026-08-03T08:30:00+07:00", "held_until": ""}]

    with pytest.raises(BookingError) as error:
        ImportService._normalize_slot_timestamps(rows, filename="06_test_drive_slots.csv")

    assert error.value.code == "INVALID_INPUT"


# test case of Chau + kiểm tra import dataset rollback toàn bộ khi file sau có header sai
def test_import_eval_dataset_is_atomic(booking_service, booking_db):
    model_csv = (
        "id,code,name,vehicle_type,required_license_class,license_requirement_note,is_active,created_at,updated_at\n"
        "model_atomic,VFA,Atomic Model,SUV,B1,GPLX B1,1,2026-08-03T00:00:00+00:00,2026-08-03T00:00:00+00:00\n"
    )
    invalid_variant_csv = "id,wrong_header\nvariant_atomic,value\n"

    with pytest.raises(BookingError) as error:
        booking_service.import_eval_dataset(
            {
                "01_vehicle_models.csv": model_csv,
                "02_vehicle_variants.csv": invalid_variant_csv,
            }
        )

    assert error.value.code == "INVALID_INPUT"
    with booking_db.connect() as connection:
        count = connection.execute("SELECT count(*) FROM vehicle_models WHERE id='model_atomic'").fetchone()[0]
    assert count == 0


def test_import_eval_dataset_uses_executemany_batches(booking_service, monkeypatch):
    model_csv = (
        "id,code,name,vehicle_type,required_license_class,license_requirement_note,is_active,created_at,updated_at\n"
        "model_batch_1,VFB1,Batch One,SUV,B1,GPLX B1,1,2026-08-03T00:00:00+00:00,2026-08-03T00:00:00+00:00\n"
        "model_batch_2,VFB2,Batch Two,SUV,B1,GPLX B1,1,2026-08-03T00:00:00+00:00,2026-08-03T00:00:00+00:00\n"
    )
    batch_sizes = []
    original_executemany = SQLiteConnection.executemany

    def track_executemany(connection, sql, params):
        batch = list(params)
        if sql.startswith("INSERT INTO vehicle_models"):
            batch_sizes.append(len(batch))
        return original_executemany(connection, sql, batch)

    monkeypatch.setattr(SQLiteConnection, "executemany", track_executemany)

    result = booking_service.import_eval_dataset({"01_vehicle_models.csv": model_csv})

    assert result["imported"]["vehicle_models"] == 2
    assert batch_sizes == [2]


# test case of Chau + kiểm tra dashboard trả số lượng booking slot và không lộ contact GPLX
def test_dashboard_returns_operational_summary_without_sensitive_fields(booking_service, confirmed_booking_factory):
    confirmed_booking_factory()

    dashboard = booking_service.get_dashboard(limit=50)

    assert dashboard["booking_counts"]["confirmed"] == 1
    assert dashboard["slot_counts"]["booked"] == 1
    assert dashboard["pending_notification_jobs"] in (3, 6)
    assert len(dashboard["recent_bookings"]) == 1
    recent = dashboard["recent_bookings"][0]
    assert "phone" not in recent
    assert "email" not in recent
    assert "license_number" not in recent
