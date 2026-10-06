from datetime import timedelta

import pytest
from src.services.booking import BookingError, iso

from tests.conftest import BOOKER_PHONE, FIXED_NOW


# Tên showroom trả candidate để khách xác nhận, không tự đi thẳng vào chọn slot.
def test_search_options_returns_showroom_query_candidate(booking_service, catalog):
    result = booking_service.search_options(vehicle_model="VF6", showroom_query="Quận 7")

    assert result["search_stage"] == "showroom_selection"
    assert result["showrooms"][0]["id"] == catalog["showroom_q7"]
    assert result["slots"] == []


def test_search_options_returns_natural_language_showroom_candidate(booking_service, catalog):
    result = booking_service.search_options(vehicle_model="VF6", showroom_query="Tôi muốn đi VinFast Quận 7")

    assert result["search_stage"] == "showroom_selection"
    assert result["showrooms"][0]["id"] == catalog["showroom_q7"]
    assert result["slots"] == []


# test case of Chau + kiểm tra từ chối vehicle variant không tồn tại
def test_search_options_rejects_unknown_variant(booking_service, catalog):
    with pytest.raises(BookingError) as error:
        booking_service.search_options(vehicle_model="VF6", vehicle_variant="Unknown")

    assert error.value.code == "VEHICLE_NOT_FOUND"


# test case of Chau + kiểm tra từ chối showroom query không tồn tại
def test_search_options_rejects_unknown_showroom_query(booking_service, catalog):
    with pytest.raises(BookingError) as error:
        booking_service.search_options(vehicle_model="VF6", showroom_query="Showroom Sao Hỏa")

    assert error.value.code == "SHOWROOM_NOT_FOUND"


# test case of Chau + kiểm tra showroom id không tồn tại phải trả lỗi thay vì response rỗng
def test_search_options_rejects_unknown_showroom_id(booking_service, catalog):
    with pytest.raises(BookingError) as error:
        booking_service.search_options(vehicle_model="VF6", showroom_id="missing-showroom")

    assert error.value.code == "SHOWROOM_NOT_FOUND"


# test case of Chau + kiểm tra giờ đúng cú pháp nhưng ngoài phạm vi 24 giờ bị từ chối
@pytest.mark.parametrize("preferred_time", ["24:00", "25:99", "-1:30"])
def test_search_options_rejects_out_of_range_time(booking_service, catalog, preferred_time):
    with pytest.raises(BookingError) as error:
        booking_service.search_options(
            vehicle_model="VF6",
            showroom_id=catalog["showroom_q7"],
            preferred_time=preferred_time,
        )

    assert error.value.code == "INVALID_INPUT"


# test case of Chau + kiểm tra slot cùng giờ của hai xe vật lý khác nhau vẫn được giữ
def test_same_time_slots_of_different_vehicles_can_both_be_held(booking_service, catalog):
    first = booking_service.hold_slot(catalog["slot_main"], "hold:different-car-one")
    second = booking_service.hold_slot(catalog["slot_second_vehicle"], "hold:different-car-two")

    assert first["booking_id"] != second["booking_id"]
    assert first["status"] == second["status"] == "held"


# test case of Chau + kiểm tra đọc draft với booking id không tồn tại
def test_get_booking_draft_rejects_unknown_booking(booking_service, catalog):
    with pytest.raises(BookingError) as error:
        booking_service.get_booking_draft("missing-booking")

    assert error.value.code == "BOOKING_DRAFT_NOT_AVAILABLE"


# test case of Chau + kiểm tra không thể chọn Driver giống Booker khi chưa nhập Booker
def test_update_draft_same_driver_requires_booker_first(booking_service, catalog):
    held = booking_service.hold_slot(catalog["slot_main"], "hold:same-driver-no-booker")

    with pytest.raises(BookingError) as error:
        booking_service.update_booking_draft(held["booking_id"], driver_same_as_booker=True, expected_version=1)

    assert error.value.code == "INVALID_INPUT"


# test case of Chau + kiểm tra partial patch chỉ đổi phone không bắt nhập lại full name
def test_update_draft_allows_partial_person_patch(booking_service, ready_draft_factory):
    prepared = ready_draft_factory()

    updated = booking_service.update_booking_draft(
        prepared["booking_id"],
        booker_patch={"phone": "0988888888"},
        expected_version=prepared["draft"]["version"],
    )

    assert updated["booker"]["full_name"] == "Huynh Thi Hai Chau"
    assert updated["booker"]["phone"] == "0988888888"


# test case of Chau + kiểm tra cam kết có GPLX là đủ mà không cần nhập số hoặc hạng GPLX
def test_draft_accepts_boolean_license_commitment_without_legacy_fields(booking_service, catalog):
    held = booking_service.hold_slot(catalog["slot_main"], "hold:boolean-license-commitment")

    draft = booking_service.update_booking_draft(
        held["booking_id"],
        booker_patch={"full_name": "Huynh Thi Hai Chau", "phone": BOOKER_PHONE, "email": "chau@example.test"},
        driver_same_as_booker=True,
        license_patch={"has_driving_license": True},
        expected_version=1,
    )

    assert draft["is_ready_to_confirm"] is True
    assert not any(field.startswith("license.") for field in draft["missing_required_fields"])


# test case of Chau + kiểm tra confirm từ chối khi hold đã hết hạn
def test_confirm_booking_rejects_expired_hold(booking_service, ready_draft_factory):
    prepared = ready_draft_factory()
    booking_service.now = lambda: FIXED_NOW + timedelta(minutes=16)

    with pytest.raises(BookingError) as error:
        booking_service.confirm_booking(prepared["booking_id"], "confirm:expired", prepared["draft"]["version"])

    assert error.value.code == "HOLD_EXPIRED"


# test case of Chau + kiểm tra confirm từ chối khi slot không còn thuộc booking
def test_confirm_booking_rejects_slot_ownership_mismatch(booking_service, booking_db, ready_draft_factory, catalog):
    prepared = ready_draft_factory()
    with booking_db.transaction(immediate=True) as connection:
        connection.execute(
            "UPDATE test_drive_slots SET current_booking_id=NULL WHERE id=?",
            (catalog["slot_main"],),
        )

    with pytest.raises(BookingError) as error:
        booking_service.confirm_booking(prepared["booking_id"], "confirm:wrong-owner", prepared["draft"]["version"])

    assert error.value.code == "SLOT_NO_LONGER_AVAILABLE"


# test case of Chau + kiểm tra booking sát giờ không tạo reminder có scheduled_at trong quá khứ
def test_confirm_booking_does_not_schedule_past_reminders(booking_service, booking_db, ready_draft_factory, catalog):
    start = FIXED_NOW + timedelta(hours=1)
    with booking_db.transaction(immediate=True) as connection:
        connection.execute(
            "UPDATE test_drive_slots SET start_at=?,end_at=? WHERE id=?",
            (
                iso(start),
                iso(start + timedelta(minutes=30)),
                catalog["slot_main"],
            ),
        )
    prepared = ready_draft_factory()
    booking_service.confirm_booking(prepared["booking_id"], "confirm:near-start", prepared["draft"]["version"])

    with booking_db.connect() as connection:
        past_jobs = connection.execute(
            "SELECT * FROM notification_jobs WHERE booking_id=? AND scheduled_at<?",
            (prepared["booking_id"], iso(FIXED_NOW)),
        ).fetchall()
    assert past_jobs == []


# test case of Chau + kiểm tra OTP challenge id không tồn tại bị từ chối
def test_verify_access_rejects_unknown_challenge(booking_service, catalog):
    with pytest.raises(BookingError) as error:
        booking_service.verify_access("missing-challenge", "123456")

    assert error.value.code == "OTP_INVALID"


# test case of Chau + kiểm tra preferred OTP channel ngoài SMS và email bị từ chối
def test_request_access_rejects_unsupported_channel(booking_service, confirmed_booking_factory):
    confirmed = confirmed_booking_factory()

    with pytest.raises(BookingError) as error:
        booking_service.request_access(
            confirmed["confirmed"]["booking_code"],
            BOOKER_PHONE,
            "lookup",
            preferred_channel="telegram",
        )

    assert error.value.code == "INVALID_INPUT"


# test case of Chau + kiểm tra request OTP liên tục trong retry window bị rate limit
def test_request_access_enforces_retry_window(booking_service, confirmed_booking_factory):
    confirmed = confirmed_booking_factory()
    booking_service.request_access(confirmed["confirmed"]["booking_code"], BOOKER_PHONE, "lookup")

    with pytest.raises(BookingError):
        booking_service.request_access(confirmed["confirmed"]["booking_code"], BOOKER_PHONE, "lookup")


# test case of Chau + kiểm tra session đã revoke không đọc được booking
def test_revoked_access_session_is_rejected(booking_service, booking_db, access_factory):
    access = access_factory("lookup")
    with booking_db.transaction(immediate=True) as connection:
        connection.execute(
            "UPDATE booking_access_sessions SET revoked_at=? WHERE booking_id=?",
            (iso(FIXED_NOW), access["booking"]["booking_id"]),
        )

    with pytest.raises(BookingError) as error:
        booking_service.get_booking_details(
            access["session"]["access_session_token"],
            booking_id=access["booking"]["booking_id"],
        )

    assert error.value.code == "ACCESS_SESSION_EXPIRED"


# test case of Chau + kiểm tra booking code không cùng scope access session bị từ chối
def test_get_booking_details_rejects_mismatched_booking_code(booking_service, access_factory):
    access = access_factory("lookup")

    with pytest.raises(BookingError) as error:
        booking_service.get_booking_details(
            access["session"]["access_session_token"],
            booking_code="VF-WRONG-CODE",
        )

    assert error.value.code == "ACCESS_SESSION_SCOPE_MISMATCH"


# test case of Chau + kiểm tra token lookup không được giữ slot dời lịch
def test_hold_reschedule_rejects_wrong_permission(booking_service, access_factory, catalog):
    access = access_factory("lookup")

    with pytest.raises(BookingError) as error:
        booking_service.hold_reschedule_slot(
            access["booking"]["booking_id"],
            catalog["slot_second_vehicle"],
            access["session"]["access_session_token"],
            "reschedule-hold:with-lookup",
        )

    assert error.value.code == "ACCESS_DENIED"


# test case of Chau + kiểm tra confirm reschedule từ chối hold lịch mới đã hết hạn
def test_confirm_reschedule_rejects_expired_new_hold(booking_service, access_factory, catalog):
    access = access_factory("reschedule")
    held = booking_service.hold_reschedule_slot(
        access["booking"]["booking_id"],
        catalog["slot_second_vehicle"],
        access["session"]["access_session_token"],
        "reschedule-hold:expiring",
    )
    booking_service.now = lambda: FIXED_NOW + timedelta(minutes=16)

    with pytest.raises(BookingError) as error:
        booking_service.confirm_reschedule(
            access["booking"]["booking_id"],
            held["booking_id"],
            access["session"]["access_session_token"],
            "reschedule-confirm:expired",
        )

    assert error.value.code == "HOLD_EXPIRED"


# test case of Chau + kiểm tra hủy booking lần hai bằng action id khác bị từ chối
def test_cancel_booking_second_distinct_action_is_rejected(booking_service, access_factory):
    access = access_factory("cancel")
    booking_service.cancel_booking(
        access["booking"]["booking_id"],
        access["session"]["access_session_token"],
        "cancel:first-action",
    )

    with pytest.raises(BookingError) as error:
        booking_service.cancel_booking(
            access["booking"]["booking_id"],
            access["session"]["access_session_token"],
            "cancel:second-action",
        )

    assert error.value.code == "BOOKING_NOT_CANCELLABLE"


# test case of Chau + kiểm tra importer báo thiếu foreign key dependency
def test_import_eval_dataset_rejects_missing_parent_reference(booking_service, catalog):
    variant_csv = (
        "id,model_id,code,name,battery_capacity_kwh,estimated_range_km,"
        "motor_power_kw,is_active,created_at,updated_at\n"
        "variant_orphan,missing_model,ORPHAN,Orphan,50,300,100,1,"
        "2026-08-03T00:00:00+00:00,2026-08-03T00:00:00+00:00\n"
    )

    with pytest.raises(BookingError) as error:
        booking_service.import_eval_dataset({"02_vehicle_variants.csv": variant_csv})

    assert error.value.code == "MISSING_DEPENDENCY"


# test case of Chau + kiểm tra import showroom từ chối latitude longitude ngoài phạm vi địa lý
@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [(91, 106.7), (-91, 106.7), (10.7, 181), (10.7, -181)],
)
def test_import_showrooms_rejects_out_of_range_coordinates(booking_service, latitude, longitude):
    csv_text = f"code,name,address,latitude,longitude\nBAD-COORD,Invalid Coordinate,Test,{latitude},{longitude}\n"

    with pytest.raises(BookingError) as error:
        booking_service.import_showrooms_csv(csv_text)

    assert error.value.code == "INVALID_INPUT"


# test case of Chau + kiểm tra dashboard không đếm hold đã hết hạn là active hold
def test_dashboard_excludes_expired_hold_from_active_count(booking_service, catalog):
    booking_service.hold_slot(catalog["slot_main"], "hold:dashboard-expired-hold")
    booking_service.now = lambda: FIXED_NOW + timedelta(minutes=16)

    result = booking_service.get_dashboard()

    assert result["active_holds"] == 0
