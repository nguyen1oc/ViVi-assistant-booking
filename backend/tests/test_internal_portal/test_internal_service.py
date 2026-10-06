from datetime import UTC, datetime, timedelta, timezone

import pytest
from src.internal_portal import InternalPortalError, InternalPortalService


def _seed_staff(database, catalog):
    created = "2026-08-03T02:00:00+00:00"
    with database.transaction(immediate=True) as connection:
        connection.executemany(
            """INSERT INTO sales_staff(
                id,showroom_id,employee_code,full_name,phone,email,role,status,is_active,created_at,updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            [
                (
                    "staff_q7",
                    catalog["showroom_q7"],
                    "IP-Q7",
                    "Staff Q7",
                    "0901000001",
                    "staff.q7@example.test",
                    "sales_consultant",
                    "active",
                    1,
                    created,
                    created,
                ),
                (
                    "staff_q7_other",
                    catalog["showroom_q7"],
                    "IP-Q7-OTHER",
                    "Other Q7",
                    "0901000002",
                    "other.q7@example.test",
                    "sales_consultant",
                    "active",
                    1,
                    created,
                    created,
                ),
            ],
        )


def _principal(service, **kwargs):
    password = "StrongPortal!2026"
    user = service.create_user(password=password, display_name="Portal User", **kwargs)
    token = service.login(user["username"], password)["access_token"]
    return service.authenticate(token), token


def test_internal_login_is_scoped_and_revocable(booking_db, catalog):
    _seed_staff(booking_db, catalog)
    service = InternalPortalService(booking_db)
    principal, token = _principal(
        service,
        username="staff.q7",
        role="staff",
        staff_id="staff_q7",
        showroom_ids=[],
    )

    assert principal.staff_id == "staff_q7"
    assert principal.showroom_ids == (catalog["showroom_q7"],)
    assert service.list_showrooms(principal)[0]["id"] == catalog["showroom_q7"]

    service.logout(token)
    with pytest.raises(InternalPortalError) as error:
        service.authenticate(token)
    assert error.value.code == "SESSION_INVALID"


def test_internal_password_minimum_is_eight_characters(booking_db):
    service = InternalPortalService(booking_db)

    created = service.create_user(
        username="eight.chars",
        password="12345678",
        display_name="Eight Characters",
        role="operations_admin",
    )
    assert service.login(created["username"], "12345678")["user"]["id"] == created["id"]

    with pytest.raises(InternalPortalError) as error:
        service.create_user(
            username="seven.chars",
            password="1234567",
            display_name="Seven Characters",
            role="operations_admin",
        )
    assert error.value.code == "WEAK_PASSWORD"


def test_operations_admin_can_manage_internal_users(booking_db, catalog):
    _seed_staff(booking_db, catalog)
    service = InternalPortalService(booking_db)
    operations_admin, _ = _principal(
        service,
        username="ops.accounts",
        role="operations_admin",
        staff_id=None,
        showroom_ids=[],
    )

    created = service.create_managed_user(
        operations_admin,
        username="staff.account",
        password="12345678",
        display_name="Staff Account",
        role="staff",
        staff_id="staff_q7",
        showroom_ids=[],
    )
    users = service.list_internal_users(operations_admin)

    assert created["showroom_ids"] == [catalog["showroom_q7"]]
    assert next(item for item in users if item["id"] == created["id"])["staff_name"] == "Staff Q7"
    assert service.list_audit_events(operations_admin)[0]["action"] == "internal_user.created"

    manager, _ = _principal(
        service,
        username="manager.accounts",
        role="showroom_manager",
        staff_id=None,
        showroom_ids=[catalog["showroom_q7"]],
    )
    assert service.list_audit_events(manager) == []
    with pytest.raises(InternalPortalError) as error:
        service.create_managed_user(
            manager,
            username="forbidden.account",
            password="12345678",
            display_name="Forbidden Account",
            role="operations_admin",
        )
    assert error.value.code == "ACCESS_DENIED"


def test_manager_cannot_cross_showroom_scope(booking_db, catalog):
    service = InternalPortalService(booking_db)
    principal, _ = _principal(
        service,
        username="manager.q7",
        role="showroom_manager",
        staff_id=None,
        showroom_ids=[catalog["showroom_q7"]],
    )

    assert [item["id"] for item in service.list_showrooms(principal)] == [catalog["showroom_q7"]]
    with pytest.raises(InternalPortalError) as error:
        service.list_vehicles(principal, showroom_id=catalog["showroom_gv"])
    assert error.value.code == "ACCESS_DENIED"


def test_dashboard_charts_are_scoped_and_cover_operational_windows(
    booking_db,
    catalog,
    confirmed_booking_factory,
):
    confirmed_booking_factory(catalog["slot_main"])
    service = InternalPortalService(booking_db, now=lambda: datetime(2026, 8, 3, 2, 0, tzinfo=UTC))
    q7_manager, _ = _principal(
        service,
        username="manager.dashboard.q7",
        role="showroom_manager",
        staff_id=None,
        showroom_ids=[catalog["showroom_q7"]],
    )
    gv_manager, _ = _principal(
        service,
        username="manager.dashboard.gv",
        role="showroom_manager",
        staff_id=None,
        showroom_ids=[catalog["showroom_gv"]],
    )

    q7_dashboard = service.dashboard(q7_manager)
    gv_dashboard = service.dashboard(gv_manager)
    booking_day = catalog["primary_start"].date().isoformat()
    q7_trend = next(point for point in q7_dashboard["booking_trend"] if point["date"] == booking_day)
    gv_trend = next(point for point in gv_dashboard["booking_trend"] if point["date"] == booking_day)
    q7_capacity = next(point for point in q7_dashboard["slot_utilization"] if point["date"] == booking_day)

    assert len(q7_dashboard["booking_trend"]) == 14
    assert q7_dashboard["booking_trend"][0]["date"] == "2026-07-28"
    assert q7_dashboard["booking_trend"][-1]["date"] == "2026-08-10"
    assert len(q7_dashboard["slot_utilization"]) == 7
    assert q7_trend["total"] == 1
    assert gv_trend["total"] == 0
    assert q7_capacity["booked"] == 1
    assert q7_capacity["total"] > q7_capacity["booked"]
    assert q7_capacity["utilization_percent"] > 0


def test_staff_only_sees_assigned_booking(booking_db, booking_service, catalog, confirmed_booking_factory):
    _seed_staff(booking_db, catalog)
    booking = confirmed_booking_factory()
    service = InternalPortalService(booking_db)
    assigned, _ = _principal(
        service,
        username="assigned.staff",
        role="staff",
        staff_id="staff_q7",
        showroom_ids=[],
    )
    other, _ = _principal(
        service,
        username="other.staff",
        role="staff",
        staff_id="staff_q7_other",
        showroom_ids=[],
    )

    assert service.list_bookings(assigned)["total"] == 1
    assert service.list_bookings(other)["total"] == 0
    service.assert_staff_booking_access(assigned, booking["booking_id"])
    with pytest.raises(InternalPortalError) as error:
        service.assert_staff_booking_access(other, booking["booking_id"])
    assert error.value.code == "ACCESS_DENIED"


def test_booking_detail_exposes_scoped_customer_profile(
    booking_db,
    catalog,
    confirmed_booking_factory,
):
    q7_booking = confirmed_booking_factory(catalog["slot_main"])
    confirmed_booking_factory(catalog["slot_gv"])
    service = InternalPortalService(booking_db)
    operations_admin, _ = _principal(
        service,
        username="ops.customer-profile",
        role="operations_admin",
        staff_id=None,
        showroom_ids=[],
    )
    q7_manager, _ = _principal(
        service,
        username="manager.customer-profile",
        role="showroom_manager",
        staff_id=None,
        showroom_ids=[catalog["showroom_q7"]],
    )

    admin_profile = service.get_booking(operations_admin, q7_booking["booking_id"])["customer_profile"]
    manager_profile = service.get_booking(q7_manager, q7_booking["booking_id"])["customer_profile"]

    assert admin_profile["full_name"] == "Huynh Thi Hai Chau"
    assert admin_profile["preferred_channel"] == "sms"
    assert admin_profile["booker_is_driver"] is True
    assert admin_profile["license"]["declared_license_class"] == "B1"
    assert admin_profile["license"]["validity_acknowledged"] is True
    assert admin_profile["summary"]["total_bookings"] == 2
    assert len(admin_profile["history"]) == 2
    assert admin_profile["vehicle_interests"] == [{"model": "VF6", "booking_count": 2}]

    # Customer history follows the same scope as the booking list. A showroom
    # manager must not learn that the same contact booked at another showroom.
    assert manager_profile["summary"]["total_bookings"] == 1
    assert {item["showroom_name"] for item in manager_profile["history"]} == {"VinFast Quận 7"}


def test_manager_account_requires_exactly_one_showroom(booking_db, catalog):
    service = InternalPortalService(booking_db)

    for showroom_ids in ([], [catalog["showroom_q7"], catalog["showroom_gv"]]):
        with pytest.raises(InternalPortalError) as error:
            service.create_user(
                username=f"manager.scope.{len(showroom_ids)}",
                password="StrongPortal!2026",
                display_name="Manager Scope",
                role="showroom_manager",
                showroom_ids=showroom_ids,
            )
        assert error.value.code == "MANAGER_SINGLE_SHOWROOM_REQUIRED"


def test_staff_cannot_read_fleet_catalog_or_showroom_aggregates(booking_db, catalog):
    _seed_staff(booking_db, catalog)
    service = InternalPortalService(booking_db)
    principal, _ = _principal(
        service,
        username="staff.private",
        role="staff",
        staff_id="staff_q7",
        showroom_ids=[],
    )

    dashboard = service.dashboard(principal)
    assert dashboard["staff_total"] == 1
    assert dashboard["vehicle_total"] == 0
    with pytest.raises(InternalPortalError) as fleet_error:
        service.list_vehicles(principal)
    assert fleet_error.value.code == "ACCESS_DENIED"
    with pytest.raises(InternalPortalError) as catalog_error:
        service.list_catalog(principal)
    assert catalog_error.value.code == "ACCESS_DENIED"


def test_staff_scope_is_derived_and_tracks_active_employment(booking_db, catalog):
    _seed_staff(booking_db, catalog)
    service = InternalPortalService(booking_db)
    with pytest.raises(InternalPortalError) as scope_error:
        service.create_user(
            username="staff.extra-scope",
            password="StrongPortal!2026",
            display_name="Extra Scope",
            role="staff",
            staff_id="staff_q7",
            showroom_ids=[catalog["showroom_gv"]],
        )
    assert scope_error.value.code == "STAFF_SCOPE_DERIVED"
    with pytest.raises(InternalPortalError) as manager_binding_error:
        service.create_user(
            username="manager.with-staff",
            password="StrongPortal!2026",
            display_name="Manager With Staff",
            role="showroom_manager",
            staff_id="staff_q7",
            showroom_ids=[catalog["showroom_q7"]],
        )
    assert manager_binding_error.value.code == "ROLE_SCOPE_MISMATCH"
    with pytest.raises(InternalPortalError) as admin_scope_error:
        service.create_user(
            username="ops.scoped",
            password="StrongPortal!2026",
            display_name="Scoped Admin",
            role="operations_admin",
            showroom_ids=[catalog["showroom_q7"]],
        )
    assert admin_scope_error.value.code == "ROLE_SCOPE_MISMATCH"

    principal, token = _principal(
        service,
        username="staff.mobile",
        role="staff",
        staff_id="staff_q7",
        showroom_ids=[],
    )
    assert principal.showroom_ids == (catalog["showroom_q7"],)
    with booking_db.transaction(immediate=True) as connection:
        connection.execute(
            "UPDATE sales_staff SET showroom_id=? WHERE id=?",
            (catalog["showroom_gv"], "staff_q7"),
        )
    assert service.authenticate(token).showroom_ids == (catalog["showroom_gv"],)

    with booking_db.transaction(immediate=True) as connection:
        connection.execute("UPDATE sales_staff SET status='inactive',is_active=0 WHERE id=?", ("staff_q7",))
    with pytest.raises(InternalPortalError) as session_error:
        service.authenticate(token)
    assert session_error.value.code == "SESSION_INVALID"
    with pytest.raises(InternalPortalError) as login_error:
        service.login("staff.mobile", "StrongPortal!2026")
    assert login_error.value.code == "ACCOUNT_INACTIVE"


def test_direct_booking_owner_does_not_bypass_active_slot_assignment(
    booking_db, catalog, confirmed_booking_factory
):
    _seed_staff(booking_db, catalog)
    booking = confirmed_booking_factory()
    service = InternalPortalService(booking_db)
    staff, _ = _principal(
        service,
        username="staff.assignment",
        role="staff",
        staff_id="staff_q7",
        showroom_ids=[],
    )
    with booking_db.transaction(immediate=True) as connection:
        connection.execute(
            "UPDATE bookings SET assigned_sales_staff_id=? WHERE id=?",
            ("staff_q7", booking["booking_id"]),
        )
        connection.execute(
            "UPDATE slot_sales_assignments SET status='reassigned' WHERE slot_id=?",
            (catalog["slot_main"],),
        )
    assert service.list_bookings(staff)["total"] == 0
    with pytest.raises(InternalPortalError) as access_error:
        service.assert_staff_booking_access(staff, booking["booking_id"])
    assert access_error.value.code == "ACCESS_DENIED"

    with booking_db.transaction(immediate=True) as connection:
        connection.execute(
            "UPDATE slot_sales_assignments SET status='assigned' "
            "WHERE slot_id=? AND sales_staff_id=? AND assignment_role='test_drive_consultant'",
            (catalog["slot_main"], "staff_q7"),
        )
    assert service.list_bookings(staff)["total"] == 1
    service.assert_staff_booking_access(staff, booking["booking_id"])


def test_operations_admin_can_lock_accounts_and_last_admin_is_protected(booking_db):
    service = InternalPortalService(booking_db)
    admin, _ = _principal(
        service,
        username="ops.primary",
        role="operations_admin",
        staff_id=None,
        showroom_ids=[],
    )
    secondary = service.create_user(
        username="ops.secondary",
        password="StrongPortal!2026",
        display_name="Secondary Admin",
        role="operations_admin",
    )
    secondary_token = service.login("ops.secondary", "StrongPortal!2026")["access_token"]

    reset = service.reset_managed_user_password(
        admin,
        secondary["id"],
        password="NewStrongPortal!2026",
    )
    assert reset["sessions_revoked"] == 1
    with pytest.raises(InternalPortalError):
        service.authenticate(secondary_token)
    secondary_token = service.login("ops.secondary", "NewStrongPortal!2026")["access_token"]

    updated = service.update_managed_user(
        admin,
        secondary["id"],
        changes={"is_active": False},
    )
    assert updated["is_active"] is False
    with pytest.raises(InternalPortalError) as revoked_error:
        service.authenticate(secondary_token)
    assert revoked_error.value.code == "SESSION_INVALID"

    with pytest.raises(InternalPortalError) as last_admin_error:
        service.update_managed_user(admin, admin.user_id, changes={"is_active": False})
    assert last_admin_error.value.code == "LAST_ADMIN_REQUIRED"


def test_manager_shift_and_unavailability_are_audited(booking_db, catalog):
    _seed_staff(booking_db, catalog)
    service = InternalPortalService(booking_db)
    manager, _ = _principal(
        service,
        username="manager.schedule",
        role="showroom_manager",
        staff_id=None,
        showroom_ids=[catalog["showroom_q7"]],
    )
    start = catalog["primary_start"] - timedelta(hours=2)
    end = catalog["primary_start"] + timedelta(hours=2)
    shift = service.create_shift(
        manager,
        staff_id="staff_q7",
        showroom_id=catalog["showroom_q7"],
        start_at=start.isoformat(),
        end_at=end.isoformat(),
    )
    unavailable = service.create_unavailability(
        manager,
        staff_id="staff_q7",
        showroom_id=catalog["showroom_q7"],
        start_at=start.isoformat(),
        end_at=end.isoformat(),
        reason="Training",
    )

    assert shift["status"] == "scheduled"
    assert unavailable["reason"] == "Training"
    assert service.list_shifts(manager)[0]["status"] == "cancelled"
    assert [event["action"] for event in service.list_audit_events(manager)] == [
        "staff.unavailability_created",
        "shift.created",
    ]


def test_portal_conflicts_compare_mixed_timezone_offsets(
    booking_db, catalog, confirmed_booking_factory
):
    _seed_staff(booking_db, catalog)
    booking = confirmed_booking_factory()
    local_timezone = timezone(timedelta(hours=7))
    local_start = catalog["primary_start"].astimezone(local_timezone)
    local_end = (catalog["primary_start"] + timedelta(minutes=30)).astimezone(local_timezone)
    with booking_db.transaction(immediate=True) as connection:
        connection.execute(
            "UPDATE test_drive_slots SET start_at=?,end_at=? WHERE id=?",
            (local_start.isoformat(), local_end.isoformat(), catalog["slot_main"]),
        )
    service = InternalPortalService(booking_db)
    manager, _ = _principal(
        service,
        username="manager.timezone",
        role="showroom_manager",
        staff_id=None,
        showroom_ids=[catalog["showroom_q7"]],
    )
    service.create_unavailability(
        manager,
        staff_id="staff_q7",
        showroom_id=catalog["showroom_q7"],
        start_at=(catalog["primary_start"] - timedelta(minutes=10)).isoformat(),
        end_at=(catalog["primary_start"] + timedelta(minutes=10)).isoformat(),
        reason="Mixed offset test",
    )

    with pytest.raises(InternalPortalError) as staff_error:
        service.assign_booking(manager, booking["booking_id"], staff_id="staff_q7")
    assert staff_error.value.code == "STAFF_UNAVAILABLE"

    with pytest.raises(InternalPortalError) as vehicle_error:
        service.create_vehicle_unavailability(
            manager,
            "demo_main",
            start_at=(catalog["primary_start"] - timedelta(minutes=10)).isoformat(),
            end_at=(catalog["primary_start"] + timedelta(minutes=10)).isoformat(),
            reason="Mixed offset vehicle test",
        )
    assert vehicle_error.value.code == "VEHICLE_BOOKING_CONFLICT"
