import json
from datetime import timedelta

import pytest
from src.services.booking import BookingError


@pytest.fixture
def staff_ids(booking_db, catalog):
    created = "2026-08-03T02:00:00+00:00"
    rows = [
        (
            "staff_q7",
            catalog["showroom_q7"],
            "EMP-Q7",
            "Chau Tester",
            "0901111111",
            "chau@example.com",
            "sales_consultant",
            "active",
            1,
            created,
            created,
        ),
        (
            "staff_gv",
            catalog["showroom_gv"],
            "EMP-GV",
            "Other Showroom",
            "0902222222",
            "gv@example.com",
            "sales_consultant",
            "active",
            1,
            created,
            created,
        ),
        (
            "staff_inactive",
            catalog["showroom_q7"],
            "EMP-OFF",
            "Inactive Staff",
            "0903333333",
            "off@example.com",
            "sales_consultant",
            "inactive",
            0,
            created,
            created,
        ),
    ]
    with booking_db.transaction(immediate=True) as connection:
        connection.executemany(
            """INSERT INTO sales_staff(
                id,showroom_id,employee_code,full_name,phone,email,role,status,
                is_active,created_at,updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            rows,
        )
        connection.execute(
            "INSERT INTO slot_sales_assignments(id,slot_id,sales_staff_id,assignment_role,status,created_at,updated_at) "
            "VALUES(?,?,?,?,?,?,?)",
            (
                "assign_staff_q7",
                catalog["slot_main"],
                "staff_q7",
                "test_drive_consultant",
                "assigned",
                created,
                created,
            ),
        )
    return {"q7": "staff_q7", "gv": "staff_gv", "inactive": "staff_inactive"}


def _record_verified(booking_service, booking_id, staff_id, action_id="staff-license:verified"):
    return booking_service.record_license_check(
        booking_id,
        staff_id,
        action_id,
        original_document_presented=True,
        license_class_matches=True,
        is_currently_valid=True,
        result="verified",
    )


# test case of Chau + kiểm tra nhân viên cùng showroom xác minh GPLX và lưu đủ trạng thái kiểm tra
def test_record_license_check_verified_updates_driver_details(
    booking_service, booking_db, confirmed_booking_factory, staff_ids
):
    booking = confirmed_booking_factory()

    result = _record_verified(booking_service, booking["booking_id"], staff_ids["q7"])

    assert result["license_check_status"] == "verified"
    assert result["eligible_for_check_in"] is True
    with booking_db.connect() as connection:
        detail = connection.execute(
            "SELECT license_check_status,checked_by,checked_at,rejection_reason "
            "FROM booking_driver_details WHERE booking_id=?",
            (booking["booking_id"],),
        ).fetchone()
        event = connection.execute(
            "SELECT event_type,actor_id,payload_json FROM booking_events "
            "WHERE booking_id=? AND event_type='license_verified'",
            (booking["booking_id"],),
        ).fetchone()

    assert detail["license_check_status"] == "verified"
    assert detail["checked_by"] == staff_ids["q7"]
    assert detail["checked_at"]
    assert detail["rejection_reason"] is None
    assert event["actor_id"] == staff_ids["q7"]
    assert json.loads(event["payload_json"]) == {"staff_id": staff_ids["q7"]}


# test case of Chau + kiểm tra service từ chối giá trị kết quả kiểm tra GPLX không hợp lệ
def test_record_license_check_rejects_unknown_result(booking_service, confirmed_booking_factory, staff_ids):
    booking = confirmed_booking_factory()

    with pytest.raises(BookingError) as error:
        booking_service.record_license_check(
            booking["booking_id"],
            staff_ids["q7"],
            "staff-license:unknown",
            original_document_presented=True,
            license_class_matches=True,
            is_currently_valid=True,
            result="approved",
        )

    assert error.value.code == "INVALID_INPUT"


@pytest.mark.parametrize(
    "failed_condition",
    ["original_document_presented", "license_class_matches", "is_currently_valid"],
)
# test case of Chau + kiểm tra không được đánh dấu verified nếu một điều kiện GPLX chưa đạt
def test_record_license_check_rejects_verified_when_a_condition_is_false(
    booking_service, confirmed_booking_factory, staff_ids, failed_condition
):
    booking = confirmed_booking_factory()
    conditions = {
        "original_document_presented": True,
        "license_class_matches": True,
        "is_currently_valid": True,
    }
    conditions[failed_condition] = False

    with pytest.raises(BookingError) as error:
        booking_service.record_license_check(
            booking["booking_id"],
            staff_ids["q7"],
            f"staff-license:false-{failed_condition}",
            **conditions,
            result="verified",
        )

    assert error.value.code == "INVALID_INPUT"


@pytest.mark.parametrize("staff_key", ["gv", "inactive"])
# test case of Chau + kiểm tra nhân viên khác showroom hoặc đã vô hiệu hóa không truy cập booking
def test_staff_operation_denies_unauthorized_staff(booking_service, confirmed_booking_factory, staff_ids, staff_key):
    booking = confirmed_booking_factory()

    with pytest.raises(BookingError) as error:
        _record_verified(
            booking_service,
            booking["booking_id"],
            staff_ids[staff_key],
            f"staff-license:denied-{staff_key}",
        )

    assert error.value.code == "ACCESS_DENIED"


# test case of Chau + kiểm tra check-in bị chặn khi GPLX chưa được nhân viên xác minh
def test_check_in_requires_verified_license(booking_service, confirmed_booking_factory, staff_ids, catalog):
    booking = confirmed_booking_factory()
    booking_service.now = lambda: catalog["primary_start"]

    with pytest.raises(BookingError) as error:
        booking_service.check_in_booking(booking["booking_id"], staff_ids["q7"], "staff-checkin:no-license")

    assert error.value.code == "LICENSE_NOT_VERIFIED"


@pytest.mark.parametrize("offset", [timedelta(minutes=-60), timedelta(minutes=30)])
# test case of Chau + kiểm tra hai mốc biên âm sáu mươi và dương ba mươi phút vẫn cho check-in
def test_check_in_accepts_inclusive_time_boundaries(
    booking_service, confirmed_booking_factory, staff_ids, catalog, offset
):
    booking = confirmed_booking_factory()
    _record_verified(booking_service, booking["booking_id"], staff_ids["q7"])
    booking_service.now = lambda: catalog["primary_start"] + offset

    result = booking_service.check_in_booking(
        booking["booking_id"], staff_ids["q7"], f"staff-checkin:{offset.total_seconds()}"
    )

    assert result["status"] == "checked_in"


@pytest.mark.parametrize(
    "offset",
    [timedelta(minutes=-60, seconds=-1), timedelta(minutes=30, seconds=1)],
)
# test case of Chau + kiểm tra ngoài cửa sổ check-in chỉ một giây cũng phải bị chặn
def test_check_in_rejects_outside_time_window(booking_service, confirmed_booking_factory, staff_ids, catalog, offset):
    booking = confirmed_booking_factory()
    _record_verified(booking_service, booking["booking_id"], staff_ids["q7"])
    booking_service.now = lambda: catalog["primary_start"] + offset

    with pytest.raises(BookingError) as error:
        booking_service.check_in_booking(
            booking["booking_id"], staff_ids["q7"], f"staff-checkin:outside-{offset.total_seconds()}"
        )

    assert error.value.code == "INVALID_STATE_TRANSITION"


# test case of Chau + kiểm tra hoàn tất chuyến lái chỉ thành công sau check-in và lưu timestamp
def test_complete_test_drive_after_check_in(booking_service, booking_db, confirmed_booking_factory, staff_ids, catalog):
    booking = confirmed_booking_factory()
    _record_verified(booking_service, booking["booking_id"], staff_ids["q7"])
    booking_service.now = lambda: catalog["primary_start"]
    booking_service.check_in_booking(booking["booking_id"], staff_ids["q7"], "staff-checkin:complete-flow")

    result = booking_service.complete_test_drive(
        booking["booking_id"],
        staff_ids["q7"],
        "staff-complete:flow",
        completion_note="Customer feedback must stay out of public output",
    )

    assert result["status"] == "completed"
    with booking_db.connect() as connection:
        row = connection.execute(
            "SELECT status,completed_at FROM bookings WHERE id=?", (booking["booking_id"],)
        ).fetchone()
    assert row["status"] == "completed"
    assert row["completed_at"]


# test case of Chau + kiểm tra không được hoàn tất chuyến lái khi booking chưa check-in
def test_complete_test_drive_requires_checked_in_status(booking_service, confirmed_booking_factory, staff_ids):
    booking = confirmed_booking_factory()

    with pytest.raises(BookingError) as error:
        booking_service.complete_test_drive(booking["booking_id"], staff_ids["q7"], "staff-complete:too-early")

    assert error.value.code == "INVALID_STATE_TRANSITION"


# test case of Chau + kiểm tra không được đánh dấu no-show trước hoặc đúng mốc grace period
def test_mark_no_show_rejects_before_grace_period(booking_service, confirmed_booking_factory, staff_ids, catalog):
    booking = confirmed_booking_factory()
    booking_service.now = lambda: catalog["primary_start"] + timedelta(minutes=30)

    with pytest.raises(BookingError) as error:
        booking_service.mark_no_show(booking["booking_id"], staff_ids["q7"], "staff-noshow:boundary")

    assert error.value.code == "INVALID_STATE_TRANSITION"


# test case of Chau + kiểm tra được đánh dấu no-show ngay sau khi grace period kết thúc
def test_mark_no_show_accepts_after_grace_period(
    booking_service, booking_db, confirmed_booking_factory, staff_ids, catalog
):
    booking = confirmed_booking_factory()
    booking_service.now = lambda: catalog["primary_start"] + timedelta(minutes=30, seconds=1)

    result = booking_service.mark_no_show(
        booking["booking_id"],
        staff_ids["q7"],
        "staff-noshow:after-boundary",
        reason="Customer did not arrive",
    )

    assert result["status"] == "no_show"
    with booking_db.connect() as connection:
        status = connection.execute("SELECT status FROM bookings WHERE id=?", (booking["booking_id"],)).fetchone()[
            "status"
        ]
    assert status == "no_show"


# test case of Chau + kiểm tra action id gọi lặp trả cùng kết quả và chỉ tạo một event
def test_staff_action_is_idempotent(booking_service, booking_db, confirmed_booking_factory, staff_ids):
    booking = confirmed_booking_factory()
    first = _record_verified(booking_service, booking["booking_id"], staff_ids["q7"], "staff-license:idempotent")

    second = _record_verified(booking_service, booking["booking_id"], staff_ids["q7"], "staff-license:idempotent")

    assert second == first
    with booking_db.connect() as connection:
        count = connection.execute(
            "SELECT count(*) AS total FROM booking_events WHERE booking_id=? AND event_type='license_verified'",
            (booking["booking_id"],),
        ).fetchone()["total"]
    assert count == 1


# test case of Chau + kiểm tra tái sử dụng action id với payload khác bị phát hiện xung đột
def test_staff_action_id_reuse_with_different_payload_is_rejected(
    booking_service, confirmed_booking_factory, staff_ids
):
    booking = confirmed_booking_factory()
    action_id = "staff-license:payload-conflict"
    _record_verified(booking_service, booking["booking_id"], staff_ids["q7"], action_id)

    with pytest.raises(BookingError) as error:
        booking_service.record_license_check(
            booking["booking_id"],
            staff_ids["q7"],
            action_id,
            original_document_presented=False,
            license_class_matches=False,
            is_currently_valid=False,
            result="rejected",
            rejection_reason="Document missing",
        )

    assert error.value.code == "IDEMPOTENCY_CONFLICT"
