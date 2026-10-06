from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from zoneinfo import ZoneInfo

import pytest
from src.services.booking import BookingError
from src.services.booking import catalog as catalog_module
from src.services.booking.location_normalizer import normalize_location_tokens

from tests.conftest import FIXED_NOW


# test case of Chau + kiểm tra tìm mẫu xe bằng code không phân biệt chữ hoa/chữ thường
def test_resolve_vehicle_model_case_insensitive(booking_service, catalog):
    result = booking_service.resolve_vehicle_model("vf6")

    assert result["id"] == catalog["model"]
    assert result["code"] == "VF6"


# test case of Chau + kiểm tra báo lỗi khi mẫu xe không tồn tại
def test_resolve_vehicle_model_not_found(booking_service, catalog):
    with pytest.raises(BookingError) as error:
        booking_service.resolve_vehicle_model("VF-UNKNOWN")

    assert error.value.code == "VEHICLE_NOT_FOUND"


# test case of Chau + kiểm tra tìm showroom và sắp xếp theo khoảng cách khách hàng
def test_search_showrooms_sorted_by_distance(booking_service, catalog):
    result = booking_service.search_options(vehicle_model="VF6", latitude=10.73, longitude=106.72)

    assert result["search_stage"] == "showroom_selection"
    assert result["showrooms"][0]["id"] == catalog["showroom_q7"]
    assert result["showrooms"][0]["distance_km"] <= result["showrooms"][1]["distance_km"]


def test_address_search_filters_showrooms_and_calculates_distance(booking_service, catalog):
    result = booking_service.search_options(vehicle_model="VF6", address="Quận 7")

    assert result["search_stage"] == "showroom_selection"
    assert result["showrooms"][0]["id"] == catalog["showroom_q7"]
    assert result["target_coordinates"] is not None
    assert all("distance_km" in showroom for showroom in result["showrooms"])


def test_address_search_keeps_nearby_showroom_outside_text_matched_province(
    booking_service, booking_db, catalog, monkeypatch
):
    """A customer location must not remove a closer showroom in a neighbouring province."""
    created = FIXED_NOW.isoformat()
    starts_at = (FIXED_NOW + timedelta(days=1)).isoformat()
    ends_at = (FIXED_NOW + timedelta(days=1, minutes=30)).isoformat()
    with booking_db.transaction(immediate=True) as connection:
        connection.executemany(
            """INSERT INTO showrooms(
                id,code,name,address,latitude,longitude,timezone,is_active,created_at,updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            [
                ("showroom_da_nang", "DN", "VinFast Đà Nẵng", "Hải Châu, Đà Nẵng", 16.0678, 108.2208, "Asia/Ho_Chi_Minh", 1, created, created),
                ("showroom_tam_ky", "TK", "VinFast Tam Kỳ", "Tam Kỳ, Quảng Nam", 15.5736, 108.4740, "Asia/Ho_Chi_Minh", 1, created, created),
            ],
        )
        connection.executemany(
            """INSERT INTO demo_vehicles(
                id,showroom_id,variant_id,asset_code,operational_status,battery_soc,
                minimum_booking_soc,is_active,created_at,updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            [
                ("demo_da_nang", "showroom_da_nang", "variant_plus", "DN-01", "available", 80, 20, 1, created, created),
                ("demo_tam_ky", "showroom_tam_ky", "variant_plus", "TK-01", "available", 80, 20, 1, created, created),
            ],
        )
        connection.executemany(
            """INSERT INTO test_drive_slots(
                id,showroom_id,demo_vehicle_id,start_at,end_at,status,created_at,updated_at
            ) VALUES(?,?,?,?,?,?,?,?)""",
            [
                ("slot_da_nang", "showroom_da_nang", "demo_da_nang", starts_at, ends_at, "available", created, created),
                ("slot_tam_ky", "showroom_tam_ky", "demo_tam_ky", starts_at, ends_at, "available", created, created),
            ],
        )

    monkeypatch.setattr(catalog_module, "resolve_address_coordinates", lambda _address: catalog_module.Coordinates(15.72, 108.10))

    result = booking_service.search_options(vehicle_model="VF6", address="Quế Sơn, Quảng Nam", showroom_limit=30)

    showroom_ids = [showroom["id"] for showroom in result["showrooms"]]
    assert "showroom_da_nang" in showroom_ids
    assert showroom_ids.index("showroom_da_nang") < showroom_ids.index("showroom_tam_ky")
    assert result["showrooms"][showroom_ids.index("showroom_da_nang")]["available_slot_count"] == 1


def test_showroom_query_returns_ranked_candidates_without_auto_selecting(booking_service, catalog):
    result = booking_service.search_options(vehicle_model="VF6", showroom_query="VinFast")

    assert result["search_stage"] == "showroom_selection"
    assert result["slots"] == []
    assert {showroom["id"] for showroom in result["showrooms"]} == {catalog["showroom_q7"], catalog["showroom_gv"]}
    assert all("Khớp tên showroom" in showroom["match_reasons"] for showroom in result["showrooms"])


def test_named_showroom_in_address_field_is_resolved_only_when_unambiguous(booking_service, catalog):
    result = booking_service.search_options(vehicle_model="VF6", address="co so Go Vapp")

    assert result["search_stage"] == "showroom_selection"
    assert result["slots"] == []
    assert [showroom["id"] for showroom in result["showrooms"]] == [catalog["showroom_gv"]]
    assert result["target_coordinates"] is None


def test_broad_named_showroom_query_is_not_implicitly_resolved(booking_service, catalog):
    result = booking_service.search_options(vehicle_model="VF6", address="showroom VinFast")

    assert result["search_stage"] == "showroom_selection"
    assert {showroom["id"] for showroom in result["showrooms"]} == {
        catalog["showroom_q7"],
        catalog["showroom_gv"],
    }


@pytest.mark.parametrize("region", ["miền Bắc", "miền Trung", "miền Nam", "miền Tây", "tôi ở miền trung"])
def test_broad_region_requires_a_province_or_city(booking_service, catalog, region):
    result = booking_service.search_options(vehicle_model="VF6", address=region)

    assert result["search_stage"] == "location_clarification"
    assert result["location_scope"] == "broad_region"
    assert result["missing_fields"] == ["province_or_city"]
    assert result["showrooms"] == []
    assert "target_coordinates" not in result


def test_address_match_reuses_cached_showroom_tokens():
    catalog_module._SHOWROOM_TOKEN_CACHE.clear()
    showroom = {
        "id": "showroom-q7",
        "updated_at": "2026-08-07T00:00:00+07:00",
        "name": "VinFast Quận 7",
        "address": "Quận 7, Thành phố Hồ Chí Minh",
    }

    first = catalog_module.CatalogService._address_match_score("Quận 7", showroom)
    second = catalog_module.CatalogService._address_match_score("Hồ Chí Minh", showroom)

    assert first > 0
    assert second > 0
    assert len(catalog_module._SHOWROOM_TOKEN_CACHE) == 1

    showroom["updated_at"] = "2026-08-08T00:00:00+07:00"
    catalog_module.CatalogService._address_match_score("Quận 7", showroom)
    assert len(catalog_module._SHOWROOM_TOKEN_CACHE) == 1


@pytest.mark.parametrize(
    ("alias", "expected_tokens"),
    [
        ("HN", {"ha", "noi"}),
        ("Hà Nội", {"ha", "noi"}),
        ("HCM", {"ho", "chi", "minh"}),
        ("TP.HCM", {"ho", "chi", "minh"}),
        ("Sài Gòn", {"ho", "chi", "minh"}),
        ("SG", {"ho", "chi", "minh"}),
    ],
)
def test_location_aliases_expand_to_canonical_city_tokens(alias, expected_tokens):
    assert expected_tokens <= normalize_location_tokens(alias)


@pytest.mark.parametrize("alias", ["HCM", "TP HCM", "Sài Gòn", "SG"])
def test_city_aliases_match_showroom_location(alias):
    showroom = {
        "id": "showroom-q7",
        "updated_at": "2026-08-07T00:00:00+07:00",
        "name": "VinFast Quận 7",
        "address": "Quận 7, Thành phố Hồ Chí Minh",
    }

    assert catalog_module.CatalogService._address_match_score(alias, showroom) > 0


def test_to_vietnam_time_normalizes_utc_and_naive_timestamps():
    utc_value = catalog_module._to_vietnam_time("2026-08-07T00:00:00Z")
    offset_value = catalog_module._to_vietnam_time("2026-08-07T00:00:00+00:00")
    naive_value = catalog_module._to_vietnam_time("2026-08-07T00:00:00")

    assert utc_value == offset_value == naive_value
    assert utc_value.tzinfo == ZoneInfo("Asia/Ho_Chi_Minh")
    assert utc_value.hour == 7


# test case of Chau + kiểm tra chỉ trả slot tương lai đang available và giới hạn tối đa năm slot
def test_search_slots_returns_future_visible_slots(booking_service, catalog):
    result = booking_service.search_options(vehicle_model="VF6", showroom_id=catalog["showroom_q7"], limit=20)

    assert result["search_stage"] == "slot_selection"
    assert 0 < len(result["slots"]) <= 20
    assert all(slot["status"] in {"available", "held", "booked"} for slot in result["slots"])
    assert all(slot["start_at"] > FIXED_NOW.isoformat() for slot in result["slots"])
    assert catalog["slot_blocked"] not in {slot["id"] for slot in result["slots"]}
    assert catalog["slot_past"] not in {slot["id"] for slot in result["slots"]}


def _insert_far_future_slot(booking_db, slot_id: str):
    start = FIXED_NOW + timedelta(days=31)
    with booking_db.transaction(immediate=True) as connection:
        connection.execute(
            "INSERT INTO test_drive_slots(id,showroom_id,demo_vehicle_id,start_at,end_at,status,"
            "created_at,updated_at) VALUES(?,?,?,?,?,'available',?,?)",
            (
                slot_id,
                "showroom_q7",
                "demo_second",
                start.isoformat(),
                (start + timedelta(minutes=30)).isoformat(),
                FIXED_NOW.isoformat(),
                FIXED_NOW.isoformat(),
            ),
        )
    return start


def test_search_slots_excludes_dates_beyond_booking_window(booking_service, booking_db, catalog):
    start = _insert_far_future_slot(booking_db, "slot_beyond_window_search")

    result = booking_service.search_options(
        vehicle_model="VF6",
        showroom_id=catalog["showroom_q7"],
        preferred_date=start.date().isoformat(),
        limit=30,
    )

    assert result["slots"] == []


def test_hold_slot_rejects_dates_beyond_booking_window(booking_service, booking_db, catalog):
    _insert_far_future_slot(booking_db, "slot_beyond_window_hold")

    with pytest.raises(BookingError) as error:
        booking_service.hold_slot("slot_beyond_window_hold", "hold:beyond-window")

    assert error.value.code == "SLOT_NO_LONGER_AVAILABLE"
    assert error.value.retryable is True


def test_search_slots_excludes_past_slots_with_a_positive_utc_offset(booking_service, booking_db, catalog):
    """A +07:00 timestamp must be compared as an instant, not as text against UTC."""
    with booking_db.transaction(immediate=True) as connection:
        connection.execute(
            "UPDATE test_drive_slots SET start_at=?, end_at=? WHERE id=?",
            (
                "2026-08-03T08:30:00+07:00",  # 01:30 UTC: already past FIXED_NOW (02:00 UTC)
                "2026-08-03T10:00:00+07:00",
                catalog["slot_past"],
            ),
        )

    result = booking_service.search_options(vehicle_model="VF6", showroom_id=catalog["showroom_q7"], limit=30)

    assert catalog["slot_past"] not in {slot["id"] for slot in result["slots"]}


def test_search_slots_orders_by_preferred_time_in_vietnam_timezone(booking_service, catalog):
    result = booking_service.search_options(
        vehicle_model="VF6", showroom_id=catalog["showroom_q7"], preferred_time="19:00", limit=10
    )

    assert result["slots"][0]["id"] == catalog["slot_later"]


def test_search_slots_supports_a_single_preferred_date(booking_service, catalog):
    result = booking_service.search_options(
        vehicle_model="VF6",
        showroom_id=catalog["showroom_q7"],
        preferred_date="2026-08-05",
    )

    assert result["focused_date"] == "2026-08-05"
    assert result["requested_dates"] == []
    assert result["requested_date_range"] is None
    assert result["available_dates"] == ["2026-08-05"]
    assert result["highlighted_dates"] == ["08-05"]


def test_search_slots_supports_specific_non_contiguous_dates(booking_service, catalog):
    result = booking_service.search_options(
        vehicle_model="VF6",
        showroom_id=catalog["showroom_q7"],
        preferred_dates=["2026-08-05", "2026-08-07"],
    )

    assert result["focused_date"] is None
    assert result["requested_dates"] == ["2026-08-05", "2026-08-07"]
    assert result["available_dates"] == ["2026-08-05"]
    assert result["highlighted_dates"] == ["08-05"]


def test_search_slots_supports_an_inclusive_date_range(booking_service, catalog):
    result = booking_service.search_options(
        vehicle_model="VF6",
        showroom_id=catalog["showroom_q7"],
        preferred_date_from="2026-08-04",
        preferred_date_to="2026-08-07",
    )

    assert result["requested_date_range"] == {"from": "2026-08-04", "to": "2026-08-07"}
    assert result["available_dates"] == ["2026-08-05"]
    assert result["highlighted_dates"] == ["08-05"]


def test_date_filter_sql_rejects_untrusted_dialect():
    filters = {
        "mode": "single",
        "dates": ["2026-08-05"],
        "from": None,
        "to": None,
    }

    with pytest.raises(ValueError, match="Unsupported database dialect"):
        catalog_module._date_filter_sql(filters, dialect="sqlite) OR 1=1 --")


@pytest.mark.parametrize(
    "date_filters",
    [
        {"preferred_date_from": "2026-08-07", "preferred_date_to": "2026-08-04"},
        {"preferred_date_from": "2026-08-04"},
        {"preferred_date": "2026-08-05", "preferred_dates": ["2026-08-05"]},
        {"preferred_dates": []},
        {"preferred_date": "2026-02-31"},
    ],
)
def test_search_slots_rejects_invalid_date_filters(booking_service, catalog, date_filters):
    with pytest.raises(BookingError) as error:
        booking_service.search_options(
            vehicle_model="VF6",
            showroom_id=catalog["showroom_q7"],
            **date_filters,
        )

    assert error.value.code == "INVALID_INPUT"


# test case of Chau + kiểm tra từ chối giờ mong muốn sai định dạng
@pytest.mark.parametrize("preferred_time", ["abc", "10", "10-aa"])
def test_search_slots_rejects_invalid_preferred_time(booking_service, catalog, preferred_time):
    with pytest.raises(BookingError) as error:
        booking_service.search_options(
            vehicle_model="VF6",
            showroom_id=catalog["showroom_q7"],
            preferred_time=preferred_time,
        )

    assert error.value.code == "INVALID_INPUT"


# test case of Chau + kiểm tra giữ slot tạo booking held và liên kết slot đúng booking
def test_hold_slot_creates_booking_and_related_records(booking_service, booking_db, catalog):
    result = booking_service.hold_slot(catalog["slot_main"], "hold:001")

    assert result["status"] == "held"
    assert result["remaining_seconds"] == 300
    assert result["resolved_vehicle"] == {
        "id": "model_vf6", "code": "VF6", "name": "VinFast VF 6",
    }
    assert result["slot_id"] == catalog["slot_main"]
    assert result["start_at"] and result["end_at"]
    with booking_db.connect() as connection:
        booking = connection.execute("SELECT * FROM bookings WHERE id=?", (result["booking_id"],)).fetchone()
        slot = connection.execute("SELECT * FROM test_drive_slots WHERE id=?", (catalog["slot_main"],)).fetchone()
        detail_count = connection.execute(
            "SELECT count(*) FROM booking_driver_details WHERE booking_id=?",
            (result["booking_id"],),
        ).fetchone()[0]
        plan_count = connection.execute(
            "SELECT count(*) FROM notification_plans WHERE booking_id=?",
            (result["booking_id"],),
        ).fetchone()[0]

    assert booking["status"] == "held"
    assert slot["status"] == "held"
    assert slot["current_booking_id"] == result["booking_id"]
    assert detail_count == 1
    assert plan_count == 1


# test case of Chau + kiểm tra idempotency khi người dùng bấm giữ slot hai lần cùng action id
def test_hold_slot_is_idempotent(booking_service, booking_db, catalog):
    first = booking_service.hold_slot(catalog["slot_main"], "hold:same-action")
    second = booking_service.hold_slot(catalog["slot_main"], "hold:same-action")

    assert second == first
    with booking_db.connect() as connection:
        count = connection.execute("SELECT count(*) FROM bookings").fetchone()[0]
    assert count == 1


# test case of Chau + kiểm tra slot đã được giữ không thể tạo thêm booking khác
def test_hold_slot_rejects_second_booking(booking_service, catalog):
    booking_service.hold_slot(catalog["slot_main"], "hold:first")

    with pytest.raises(BookingError) as error:
        booking_service.hold_slot(catalog["slot_main"], "hold:second")

    assert error.value.code == "SLOT_NO_LONGER_AVAILABLE"
    assert error.value.retryable is True


def test_hold_slot_reclaims_expired_hold_before_creating_a_new_booking(booking_service, booking_db, catalog):
    first = booking_service.hold_slot(catalog["slot_main"], "hold:first-expired")
    booking_service.now = lambda: FIXED_NOW + timedelta(minutes=6)

    second = booking_service.hold_slot(catalog["slot_main"], "hold:after-expiry")

    assert second["booking_id"] != first["booking_id"]
    assert second["remaining_seconds"] == 300
    with booking_db.connect() as connection:
        first_booking = connection.execute(
            "SELECT status FROM bookings WHERE id=?", (first["booking_id"],)
        ).fetchone()
        slot = connection.execute(
            "SELECT status,current_booking_id FROM test_drive_slots WHERE id=?", (catalog["slot_main"],)
        ).fetchone()
    assert first_booking["status"] == "expired"
    assert slot["status"] == "held"
    assert slot["current_booking_id"] == second["booking_id"]


def test_releasing_an_old_hold_does_not_unlock_a_new_booking(booking_service, booking_db, catalog):
    first = booking_service.hold_slot(catalog["slot_main"], "hold:first-owner")
    with booking_db.transaction(immediate=True) as connection:
        connection.execute(
            "UPDATE test_drive_slots SET status='available',held_until=NULL,current_booking_id=NULL WHERE id=?",
            (catalog["slot_main"],),
        )
    second = booking_service.hold_slot(catalog["slot_main"], "hold:second-owner")

    booking_service.release_hold(first["booking_id"])

    with booking_db.connect() as connection:
        slot = connection.execute(
            "SELECT status,current_booking_id FROM test_drive_slots WHERE id=?", (catalog["slot_main"],)
        ).fetchone()
    assert slot["status"] == "held"
    assert slot["current_booking_id"] == second["booking_id"]


# test case of Chau + kiểm tra hai slot trùng thời gian của cùng xe không được giữ đồng thời
def test_hold_slot_rejects_overlapping_slot_of_same_vehicle(booking_service, catalog):
    booking_service.hold_slot(catalog["slot_main"], "hold:primary")

    with pytest.raises(BookingError) as error:
        booking_service.hold_slot(catalog["slot_overlap"], "hold:overlap")

    assert error.value.code == "SLOT_NO_LONGER_AVAILABLE"


def test_overlapping_slots_cannot_consume_the_same_sales_staff(
    booking_service,
    booking_db,
    catalog,
):
    """One consultant is capacity for one overlapping active appointment."""
    timestamp = FIXED_NOW.isoformat()
    with booking_db.transaction(immediate=True) as connection:
        connection.execute(
            "INSERT INTO sales_staff("
            "id,showroom_id,employee_code,full_name,role,status,is_active,created_at,updated_at"
            ") VALUES(?,?,?,?,?,'active',1,?,?)",
            (
                "staff_capacity_one",
                catalog["showroom_q7"],
                "CAPACITY-ONE",
                "Capacity Consultant",
                "sales_consultant",
                timestamp,
                timestamp,
            ),
        )
        connection.executemany(
            "INSERT INTO slot_sales_assignments("
            "id,slot_id,sales_staff_id,assignment_role,status,created_at,updated_at"
            ") VALUES(?,?,?,?,?,?,?)",
            [
                (
                    "assign_capacity_main",
                    catalog["slot_main"],
                    "staff_capacity_one",
                    "test_drive_consultant",
                    "assigned",
                    timestamp,
                    timestamp,
                ),
                (
                    "assign_capacity_second",
                    catalog["slot_second_vehicle"],
                    "staff_capacity_one",
                    "test_drive_consultant",
                    "assigned",
                    timestamp,
                    timestamp,
                ),
            ],
        )

    booking_service.hold_slot(catalog["slot_main"], "hold:staff-capacity-first")
    with pytest.raises(BookingError) as error:
        booking_service.hold_slot(catalog["slot_second_vehicle"], "hold:staff-capacity-second")

    assert error.value.code == "STAFF_NOT_AVAILABLE"


def test_search_never_offers_more_overlapping_slots_than_staff_capacity(
    booking_service,
    booking_db,
    catalog,
):
    timestamp = FIXED_NOW.isoformat()
    with booking_db.transaction(immediate=True) as connection:
        connection.execute(
            "INSERT INTO sales_staff("
            "id,showroom_id,employee_code,full_name,role,status,is_active,created_at,updated_at"
            ") VALUES(?,?,?,?,?,'active',1,?,?)",
            (
                "staff_capacity_search",
                catalog["showroom_q7"],
                "CAPACITY-SEARCH",
                "Search Capacity Consultant",
                "sales_consultant",
                timestamp,
                timestamp,
            ),
        )

    result = booking_service.search_options(
        vehicle_model="VF6",
        showroom_id=catalog["showroom_q7"],
        slot_limit=30,
    )
    overlapping = [
        slot
        for slot in result["slots"]
        if slot["id"] in {catalog["slot_main"], catalog["slot_second_vehicle"]}
    ]

    assert result["staff_capacity"]["tracked"] is True
    assert result["staff_capacity"]["active_staff_count"] == 1
    assert len(overlapping) == 1


# test case of Chau + kiểm tra hai request đồng thời chỉ có một request giữ slot thành công
def test_concurrent_hold_allows_only_one_winner(booking_service, catalog):
    barrier = Barrier(2)

    def attempt(index):
        barrier.wait()
        try:
            return booking_service.hold_slot(catalog["slot_main"], f"hold:concurrent-{index}")
        except BookingError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(attempt, [1, 2]))

    successes = [result for result in results if isinstance(result, dict)]
    failures = [result for result in results if isinstance(result, str)]
    assert len(successes) == 1
    assert failures == ["SLOT_NO_LONGER_AVAILABLE"]


# test case of Chau + kiểm tra job hết hạn hold giải phóng slot cho khách khác
def test_expire_held_booking_releases_slot(booking_service, booking_db, catalog):
    held = booking_service.hold_slot(catalog["slot_main"], "hold:to-expire")
    booking_service.now = lambda: FIXED_NOW.replace(hour=3)

    expired_count = booking_service.expire_held_bookings()

    assert expired_count == 1
    with booking_db.connect() as connection:
        booking = connection.execute("SELECT status FROM bookings WHERE id=?", (held["booking_id"],)).fetchone()
        slot = connection.execute(
            "SELECT status,current_booking_id FROM test_drive_slots WHERE id=?",
            (catalog["slot_main"],),
        ).fetchone()
    assert booking["status"] == "expired"
    assert slot["status"] == "available"
    assert slot["current_booking_id"] is None


# test case of Chau + kiểm tra không cho giữ slot với TTL bằng không hoặc âm
@pytest.mark.parametrize("ttl_seconds", [0, -1])
def test_hold_slot_rejects_non_positive_ttl(booking_service, catalog, ttl_seconds):
    with pytest.raises(BookingError) as error:
        booking_service.hold_slot(catalog["slot_main"], f"hold:invalid-ttl-{ttl_seconds}", ttl_seconds=ttl_seconds)

    assert error.value.code == "INVALID_INPUT"


# test case of Chau + kiểm tra không giữ slot của xe đang maintenance
def test_hold_slot_rejects_maintenance_vehicle(booking_service, catalog):
    with pytest.raises(BookingError) as error:
        booking_service.hold_slot(catalog["slot_maintenance"], "hold:not-ready-maintenance")

    assert error.value.code == "VEHICLE_NOT_READY"
