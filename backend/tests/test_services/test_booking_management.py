from datetime import UTC, datetime, timedelta

import pytest
from src.services.booking import BookingError
from src.services.booking.common import iso


# test case of Chau + kiểm tra token update_details được sửa thông tin Booker của booking confirmed
def test_update_booking_details_with_correct_permission(booking_service, access_factory):
    access = access_factory("update_details")

    result = booking_service.update_booking_details(
        access["booking"]["booking_id"],
        access["session"]["access_session_token"],
        booker_patch={"full_name": "Chau Updated", "email": "chau@example.com"},
    )

    assert result["booker"]["full_name"] == "Chau Updated"
    assert result["booker"]["email"] == "chau@example.com"


@pytest.mark.parametrize(
    "booker_patch",
    [
        {"full_name": "A" * 31},
        {"email": f"{'a' * 31}@example.com"},
        {"phone": "09012345678"},
    ],
)
def test_update_booking_details_rejects_customer_fields_over_limits(booking_service, access_factory, booker_patch):
    access = access_factory("update_details")

    with pytest.raises(BookingError) as error:
        booking_service.update_booking_details(
            access["booking"]["booking_id"],
            access["session"]["access_session_token"],
            booker_patch=booker_patch,
        )

    assert error.value.code == "INVALID_INPUT"


# test case of Chau + kiểm tra token lookup không được sửa thông tin Booker Driver
def test_update_booking_details_rejects_wrong_permission(booking_service, access_factory):
    access = access_factory("lookup")

    with pytest.raises(BookingError) as error:
        booking_service.update_booking_details(
            access["booking"]["booking_id"],
            access["session"]["access_session_token"],
            booker_patch={"full_name": "Unauthorized Change"},
        )

    assert error.value.code == "ACCESS_DENIED"


# test case of Chau + kiểm tra giữ slot dời lịch sao chép Booker Driver GPLX và notification plan
def test_hold_reschedule_slot_copies_booking_data(booking_service, access_factory, catalog):
    access = access_factory("reschedule")

    result = booking_service.hold_reschedule_slot(
        access["booking"]["booking_id"],
        catalog["slot_second_vehicle"],
        access["session"]["access_session_token"],
        "reschedule-hold:copy-data",
    )
    draft = booking_service.get_booking_draft(result["booking_id"])

    assert draft["status"] == "held"
    assert draft["rescheduled_from_booking_id"] == access["booking"]["booking_id"]
    assert draft["booker_person_id"] == access["booking"]["draft"]["booker_person_id"]
    assert draft["driver_person_id"] == access["booking"]["draft"]["driver_person_id"]
    assert draft["license_declaration"]["has_driving_license"] is True
    assert draft["is_ready_to_confirm"] is True


def test_search_reschedule_returns_exact_match_on_requested_date(booking_service, access_factory):
    access = access_factory("reschedule")

    result = booking_service.search_reschedule_options(
        access["booking"]["booking_id"],
        access["session"]["access_session_token"],
        date_type="explicit",
        target_date="2026-08-05",
        target_time="17:00",
    )

    assert result["status"] == "exact_match"
    assert result["match"]["difference_minutes"] == 0
    assert result["match"]["auto_hold_allowed"] is True
    assert result["match"]["slot"]["start_at"].startswith("2026-08-05T17:00")


def test_search_reschedule_allows_nearest_match_only_within_threshold(booking_service, access_factory):
    access = access_factory("reschedule")

    near = booking_service.search_reschedule_options(
        access["booking"]["booking_id"],
        access["session"]["access_session_token"],
        date_type="explicit",
        target_date="2026-08-05",
        target_time="18:30",
    )
    far = booking_service.search_reschedule_options(
        access["booking"]["booking_id"],
        access["session"]["access_session_token"],
        date_type="explicit",
        target_date="2026-08-05",
        target_time="22:00",
    )

    assert near["status"] == "nearest_match"
    assert near["match"]["difference_minutes"] == 30
    assert near["match"]["auto_hold_allowed"] is True
    assert far["status"] == "confirmation_required"
    assert far["match"]["difference_minutes"] == 180
    assert far["match"]["auto_hold_allowed"] is False


def test_search_reschedule_never_silently_selects_another_date(booking_service, access_factory):
    access = access_factory("reschedule")

    result = booking_service.search_reschedule_options(
        access["booking"]["booking_id"],
        access["session"]["access_session_token"],
        date_type="relative_to_booking",
        day_offset=1,
        target_time="17:00",
    )

    assert result["resolved_target"]["date"] == "2026-08-06"
    assert result["status"] == "no_slots_on_requested_date"
    assert result["slots"] == []
    assert result["alternatives"]


def test_search_reschedule_interprets_a_naive_clock_as_utc(booking_service, booking_db, access_factory):
    access = access_factory("reschedule")
    test_now = datetime(2026, 8, 5, 18, 0)
    booking_service.now = lambda: test_now
    # The access fixture is created at FIXED_NOW (03/08), whereas this test
    # intentionally advances the clock to inspect a timezone boundary.
    # Keep the access gate valid so the assertion below reaches date handling.
    with booking_db.transaction() as c:
        c.execute(
            "UPDATE booking_access_sessions SET expires_at=? WHERE booking_id=?",
            (iso(test_now.replace(tzinfo=UTC) + timedelta(minutes=5)), access["booking"]["booking_id"]),
        )

    result = booking_service.search_reschedule_options(
        access["booking"]["booking_id"],
        access["session"]["access_session_token"],
        date_type="relative_to_today",
        day_offset=0,
        target_time="17:00",
    )

    assert result["resolved_target"]["date"] == "2026-08-06"


def test_search_reschedule_requires_clarification_for_ambiguous_date(booking_service, access_factory):
    access = access_factory("reschedule")

    result = booking_service.search_reschedule_options(
        access["booking"]["booking_id"],
        access["session"]["access_session_token"],
        date_type="ambiguous",
        target_time="14:00",
    )

    assert result["status"] == "clarification_required"
    assert result["missing_fields"] == ["target_date"]
    assert "match" not in result


# test case of Chau + kiểm tra xác nhận dời lịch đóng booking cũ mở booking mới và chuyển slot
def test_confirm_reschedule_transitions_both_bookings(booking_service, booking_db, access_factory, catalog):
    access = access_factory("reschedule")
    old_booking_id = access["booking"]["booking_id"]
    held = booking_service.hold_reschedule_slot(
        old_booking_id,
        catalog["slot_second_vehicle"],
        access["session"]["access_session_token"],
        "reschedule-hold:success",
    )

    result = booking_service.confirm_reschedule(
        old_booking_id,
        held["booking_id"],
        access["session"]["access_session_token"],
        "reschedule-confirm:success",
    )

    assert result["old_booking_status"] == "rescheduled"
    assert result["new_booking_status"] == "confirmed"
    with booking_db.connect() as connection:
        old_booking = connection.execute("SELECT * FROM bookings WHERE id=?", (old_booking_id,)).fetchone()
        new_booking = connection.execute("SELECT * FROM bookings WHERE id=?", (held["booking_id"],)).fetchone()
        old_slot = connection.execute("SELECT * FROM test_drive_slots WHERE id=?", (catalog["slot_main"],)).fetchone()
        new_slot = connection.execute(
            "SELECT * FROM test_drive_slots WHERE id=?",
            (catalog["slot_second_vehicle"],),
        ).fetchone()
        old_pending_jobs = connection.execute(
            "SELECT count(*) FROM notification_jobs WHERE booking_id=? AND status='pending'",
            (old_booking_id,),
        ).fetchone()[0]

    assert old_booking["status"] == "rescheduled"
    assert old_booking["replaced_by_booking_id"] == held["booking_id"]
    assert new_booking["status"] == "confirmed"
    assert old_slot["status"] == "available"
    assert new_slot["status"] == "booked"
    assert old_pending_jobs == 0


def test_reschedule_booking_completes_both_steps_and_is_retry_safe(
    booking_service,
    access_factory,
    catalog,
):
    access = access_factory("manage")
    arguments = (
        access["booking"]["booking_id"],
        catalog["slot_second_vehicle"],
        access["session"]["access_session_token"],
        "reschedule:composite-success",
    )

    first = booking_service.reschedule_booking(*arguments)
    second = booking_service.reschedule_booking(*arguments)

    assert first == second
    assert first["old_booking_status"] == "rescheduled"
    assert first["new_booking_status"] == "confirmed"
    assert first["new_slot_id"] == catalog["slot_second_vehicle"]


def test_reschedule_booking_requires_public_idempotency_namespace(
    booking_service,
    access_factory,
    catalog,
):
    access = access_factory("manage")

    with pytest.raises(BookingError) as error:
        booking_service.reschedule_booking(
            access["booking"]["booking_id"],
            catalog["slot_second_vehicle"],
            access["session"]["access_session_token"],
            "wrong-prefix",
        )

    assert error.value.code == "INVALID_INPUT"


# test case of Chau + kiểm tra hủy booking giải phóng slot và dừng notification pending
def test_cancel_booking_releases_slot_and_notifications(booking_service, booking_db, access_factory, catalog):
    access = access_factory("cancel")

    result = booking_service.cancel_booking(
        access["booking"]["booking_id"],
        access["session"]["access_session_token"],
        "cancel:success",
    )

    assert result["booking_status"] == "cancelled"
    assert result["released_slot_id"] == catalog["slot_main"]
    assert result["cancelled_notification_jobs_count"] in (3, 6)
    with booking_db.connect() as connection:
        slot = connection.execute(
            "SELECT status,current_booking_id FROM test_drive_slots WHERE id=?",
            (catalog["slot_main"],),
        ).fetchone()
        booking = connection.execute(
            "SELECT status,cancellation_reason FROM bookings WHERE id=?",
            (access["booking"]["booking_id"],),
        ).fetchone()
    assert booking["status"] == "cancelled"
    assert booking["cancellation_reason"] is None
    assert slot["status"] == "available"
    assert slot["current_booking_id"] is None


# test case of Chau + kiểm tra hủy lặp lại cùng action id không tạo event hoặc side effect trùng
def test_cancel_booking_is_idempotent(booking_service, booking_db, access_factory):
    access = access_factory("cancel")
    action_id = "cancel:idempotent"

    first = booking_service.cancel_booking(
        access["booking"]["booking_id"],
        access["session"]["access_session_token"],
        action_id,
    )
    second = booking_service.cancel_booking(
        access["booking"]["booking_id"],
        access["session"]["access_session_token"],
        action_id,
    )

    assert second == first
    with booking_db.connect() as connection:
        event_count = connection.execute(
            "SELECT count(*) FROM booking_events WHERE booking_id=? AND event_type='booking_cancelled'",
            (access["booking"]["booking_id"],),
        ).fetchone()[0]
    assert event_count == 1


# test case of Chau + kiểm tra action id được phân tách theo namespace của từng operation
def test_idempotency_key_is_scoped_by_operation(booking_service, catalog):
    held = booking_service.hold_slot(catalog["slot_main"], "hold:shared")
    draft = booking_service.update_booking_draft(
        held["booking_id"],
        booker_patch={"full_name": "Huynh Thi Hai Chau", "phone": "0901234567", "email": "chau@example.test"},
        driver_same_as_booker=True,
        license_patch={
            "has_driving_license": True,
            "declared_license_class": "B1",
            "validity_acknowledged": True,
        },
        expected_version=1,
    )

    confirmed = booking_service.confirm_booking(held["booking_id"], "confirm:shared", draft["version"])

    assert confirmed["status"] == "confirmed"
    assert "booking_code" in confirmed


# test case of Chau + kiểm tra replay cancel vẫn phải xác thực access token trước khi trả cache
def test_cancel_idempotent_replay_still_requires_valid_token(booking_service, access_factory):
    access = access_factory("cancel")
    action_id = "cancel:auth-replay"
    booking_service.cancel_booking(
        access["booking"]["booking_id"],
        access["session"]["access_session_token"],
        action_id,
    )

    with pytest.raises(BookingError) as error:
        booking_service.cancel_booking(access["booking"]["booking_id"], "invalid-token", action_id)

    assert error.value.code == "ACCESS_SESSION_EXPIRED"


def test_merging_driver_back_to_booker_removes_unreferenced_clone(booking_service, booking_db, access_factory):
    access = access_factory("update_details")
    booking_id = access["booking"]["booking_id"]
    token = access["session"]["access_session_token"]

    booking_service.update_booking_details(
        booking_id,
        token,
        booker_patch={"full_name": "Huynh Thi Hai Chau"},
        driver_patch={"full_name": "Nguoi Lai Thu", "email": "driver@example.com"},
    )
    with booking_db.connect() as connection:
        driver_id = connection.execute("SELECT driver_person_id FROM bookings WHERE id=?", (booking_id,)).fetchone()[0]

    booking_service.update_booking_details(
        booking_id,
        token,
        booker_patch={"full_name": "Huynh Thi Hai Chau"},
        driver_same_as_booker=True,
    )
    with booking_db.connect() as connection:
        assert connection.execute("SELECT driver_person_id FROM bookings WHERE id=?", (booking_id,)).fetchone()[0] != driver_id
