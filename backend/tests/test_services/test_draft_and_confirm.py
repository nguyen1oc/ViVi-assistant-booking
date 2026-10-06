from datetime import timedelta

import pytest
from src.services.booking import BookingError

from tests.conftest import BOOKER_PHONE, FIXED_NOW


# test case of Chau + kiểm tra draft mới liệt kê đủ thông tin Booker Driver và GPLX còn thiếu
def test_new_draft_reports_missing_required_fields(booking_service, catalog):
    held = booking_service.hold_slot(catalog["slot_main"], "hold:missing-fields")

    draft = booking_service.get_booking_draft(held["booking_id"])

    assert draft["missing_required_fields"] == [
        "booker",
        "driver",
        "license.has_driving_license",
    ]
    assert draft["is_ready_to_confirm"] is False


# test case of Chau + kiểm tra Booker đồng thời là Driver làm draft sẵn sàng xác nhận
def test_update_draft_with_same_booker_and_driver(ready_draft_factory):
    prepared = ready_draft_factory()

    assert prepared["draft"]["is_ready_to_confirm"] is True
    assert prepared["draft"]["booker_person_id"] == prepared["draft"]["driver_person_id"]
    assert prepared["draft"]["booker"]["phone"] == BOOKER_PHONE


# test case of Chau + kiểm tra trường hợp người đặt khác người trực tiếp lái xe
def test_update_draft_with_separate_booker_and_driver(booking_service, catalog):
    held = booking_service.hold_slot(catalog["slot_main"], "hold:separate-driver")

    draft = booking_service.update_booking_draft(
        held["booking_id"],
        booker_patch={"full_name": "Huynh Thi Hai Chau", "phone": BOOKER_PHONE, "email": "chau@example.test"},
        driver_patch={"full_name": "Nguyen Van Nam", "phone": "0912345678", "email": "nam@example.test"},
        license_patch={
            "has_driving_license": True,
            "declared_license_class": "B1",
            "validity_acknowledged": True,
        },
        expected_version=1,
    )

    assert draft["is_ready_to_confirm"] is True
    assert draft["booker_person_id"] != draft["driver_person_id"]
    assert draft["driver"]["full_name"] == "Nguyen Van Nam"


def test_switching_to_same_driver_clears_previous_driver_license_declaration(booking_service, catalog):
    held = booking_service.hold_slot(catalog["slot_main"], "hold:reset-driver-license")
    separate = booking_service.update_booking_draft(
        held["booking_id"],
        booker_patch={"full_name": "Huynh Thi Hai Chau", "phone": BOOKER_PHONE, "email": "chau@example.test"},
        driver_patch={"full_name": "Nguyen Van Nam", "phone": "0912345678", "email": "nam@example.test"},
        license_patch={"has_driving_license": True, "declared_license_class": "B1", "validity_acknowledged": True},
        expected_version=1,
    )

    draft = booking_service.update_booking_draft(
        held["booking_id"], driver_same_as_booker=True, expected_version=separate["version"]
    )

    assert draft["driver_person_id"] == draft["booker_person_id"]
    assert draft["license_declaration"]["has_driving_license"] is None
    assert draft["license_declaration"]["declared_license_class"] is None


# test case of Chau + kiểm tra optimistic concurrency từ chối version cũ
def test_update_draft_rejects_stale_version(booking_service, ready_draft_factory):
    prepared = ready_draft_factory()

    with pytest.raises(BookingError) as error:
        booking_service.update_booking_draft(
            prepared["booking_id"],
            booker_patch={"full_name": "Chau Updated", "phone": BOOKER_PHONE},
            expected_version=1,
        )

    assert error.value.code == "VERSION_CONFLICT"
    assert error.value.retryable is True


# test case of Chau + kiểm tra không được cập nhật draft sau khi hold hết hạn
def test_update_draft_rejects_expired_hold_and_durably_releases_slot(booking_service, booking_db, catalog):
    held = booking_service.hold_slot(catalog["slot_main"], "hold:expired-update")
    booking_service.now = lambda: FIXED_NOW + timedelta(minutes=16)

    with pytest.raises(BookingError) as error:
        booking_service.update_booking_draft(
            held["booking_id"],
            booker_patch={"full_name": "Huynh Thi Hai Chau", "phone": BOOKER_PHONE},
            expected_version=1,
        )

    assert error.value.code == "HOLD_EXPIRED"
    with booking_db.connect() as connection:
        booking = connection.execute("SELECT status FROM bookings WHERE id=?", (held["booking_id"],)).fetchone()
        slot = connection.execute("SELECT status,current_booking_id FROM test_drive_slots WHERE id=?", (catalog["slot_main"],)).fetchone()
    assert booking["status"] == "expired"
    assert slot["status"] == "available"
    assert slot["current_booking_id"] is None


# test case of Chau + kiểm tra xác nhận booking cập nhật đúng booking slot GPLX và notification
def test_confirm_booking_updates_full_aggregate(booking_service, booking_db, ready_draft_factory, catalog):
    prepared = ready_draft_factory()

    result = booking_service.confirm_booking(prepared["booking_id"], "confirm:success", prepared["draft"]["version"])

    assert result["status"] == "confirmed"
    assert result["booking_code"].startswith("VF260803")
    with booking_db.connect() as connection:
        booking = connection.execute("SELECT * FROM bookings WHERE id=?", (prepared["booking_id"],)).fetchone()
        slot = connection.execute("SELECT * FROM test_drive_slots WHERE id=?", (catalog["slot_main"],)).fetchone()
        driver_detail = connection.execute(
            "SELECT * FROM booking_driver_details WHERE booking_id=?",
            (prepared["booking_id"],),
        ).fetchone()
        jobs = connection.execute(
            "SELECT notification_type FROM notification_jobs WHERE booking_id=?",
            (prepared["booking_id"],),
        ).fetchall()

    assert booking["status"] == "confirmed"
    assert slot["status"] == "booked"
    assert slot["current_booking_id"] == prepared["booking_id"]
    assert driver_detail["license_check_status"] == "pending_in_person"
    assert {job["notification_type"] for job in jobs} == {
        "booking_confirmation",
        "reminder_24h",
        "reminder_2h",
    }


# test case of Chau + kiểm tra không được xác nhận draft còn thiếu dữ liệu bắt buộc
def test_confirm_booking_rejects_incomplete_draft(booking_service, catalog):
    held = booking_service.hold_slot(catalog["slot_main"], "hold:confirm-incomplete")

    with pytest.raises(BookingError) as error:
        booking_service.confirm_booking(held["booking_id"], "confirm:incomplete-action", 1)

    assert error.value.code == "INVALID_INPUT"


# test case of Chau + kiểm tra xác nhận booking từ chối expected version không đúng
def test_confirm_booking_rejects_stale_version(booking_service, ready_draft_factory):
    prepared = ready_draft_factory()

    with pytest.raises(BookingError) as error:
        booking_service.confirm_booking(prepared["booking_id"], "confirm:stale", 1)

    assert error.value.code == "VERSION_CONFLICT"


# test case of Chau + kiểm tra bấm xác nhận lặp lại không tạo booking hoặc notification trùng
def test_confirm_booking_is_idempotent(booking_service, booking_db, ready_draft_factory):
    prepared = ready_draft_factory()
    action_id = "confirm:idempotent"

    first = booking_service.confirm_booking(prepared["booking_id"], action_id, prepared["draft"]["version"])
    second = booking_service.confirm_booking(prepared["booking_id"], action_id, prepared["draft"]["version"])

    assert second == first
    with booking_db.connect() as connection:
        job_count = connection.execute(
            "SELECT count(*) FROM notification_jobs WHERE booking_id=?",
            (prepared["booking_id"],),
        ).fetchone()[0]
        event_count = connection.execute(
            "SELECT count(*) FROM booking_events WHERE booking_id=? AND event_type='booking_confirmed'",
            (prepared["booking_id"],),
        ).fetchone()[0]
    assert job_count in (3, 6)
    assert event_count == 1


# test case of Chau + kiểm tra notification jobs tôn trọng lựa chọn tắt reminder của người dùng
def test_confirm_booking_respects_notification_preferences(booking_service, booking_db, ready_draft_factory):
    prepared = ready_draft_factory(
        notification_plan_patch={
            "sms_enabled": 1,
            "email_enabled": 0,
            "reminder_24h_enabled": 0,
            "reminder_2h_enabled": 0,
        }
    )

    booking_service.confirm_booking(prepared["booking_id"], "confirm:no-reminders", prepared["draft"]["version"])

    with booking_db.connect() as connection:
        job_types = {
            row["notification_type"]
            for row in connection.execute(
                "SELECT notification_type FROM notification_jobs WHERE booking_id=?",
                (prepared["booking_id"],),
            )
        }
    assert job_types == {"booking_confirmation"}


# test case of Chau + kiểm tra đổi từ Booker kiêm Driver sang Driver riêng không sửa nhầm Booker
def test_switching_to_separate_driver_preserves_booker(booking_service, ready_draft_factory):
    prepared = ready_draft_factory()

    updated = booking_service.update_booking_draft(
        prepared["booking_id"],
        driver_patch={"full_name": "Nguyen Van Nam", "phone": "0912345678", "email": "nam@example.test"},
        expected_version=prepared["draft"]["version"],
    )

    assert updated["booker"]["full_name"] == "Huynh Thi Hai Chau"
    assert updated["driver"]["full_name"] == "Nguyen Van Nam"
    assert updated["booker_person_id"] != updated["driver_person_id"]


# test case of Chau + kiểm tra draft confirmed không được đọc trực tiếp nếu chưa xác thực OTP
def test_get_draft_rejects_confirmed_booking_without_access(booking_service, confirmed_booking_factory):
    confirmed = confirmed_booking_factory()

    with pytest.raises(BookingError) as error:
        booking_service.get_booking_draft(confirmed["booking_id"])

    assert error.value.code == "BOOKING_DRAFT_NOT_AVAILABLE"
