from datetime import UTC, datetime, timedelta

import pytest
from src.internal_portal import InternalPortalService
from src.internal_portal.routes import get_internal_portal_service
from src.main import app

FIXED_NOW = datetime(2026, 8, 3, 2, 0, tzinfo=UTC)
PASSWORD = "StrongPortal!2026"


def _seed_staff(database, catalog):
    created = FIXED_NOW.isoformat()
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
                    "Staff Q7 Other",
                    "0901000002",
                    "staff.q7.other@example.test",
                    "sales_consultant",
                    "active",
                    1,
                    created,
                    created,
                ),
                (
                    "staff_gv",
                    catalog["showroom_gv"],
                    "IP-GV",
                    "Staff GV",
                    "0901000003",
                    "staff.gv@example.test",
                    "sales_consultant",
                    "active",
                    1,
                    created,
                    created,
                ),
            ],
        )


def _headers(service, *, username, role, staff_id=None, showroom_ids=None):
    service.create_user(
        username=username,
        password=PASSWORD,
        display_name=username,
        role=role,
        staff_id=staff_id,
        showroom_ids=showroom_ids or [],
    )
    token = service.login(username, PASSWORD)["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_staff_api_is_strictly_read_only_and_booking_is_assignment_scoped(
    client, booking_db, catalog, confirmed_booking_factory
):
    _seed_staff(booking_db, catalog)
    own_booking = confirmed_booking_factory(catalog["slot_main"])
    other_booking = confirmed_booking_factory(catalog["slot_second_vehicle"])
    service = InternalPortalService(booking_db, now=lambda: FIXED_NOW)
    headers = _headers(service, username="staff.routes", role="staff", staff_id="staff_q7")
    app.dependency_overrides[get_internal_portal_service] = lambda: service
    try:
        own = await client.get(
            f"/api/v1/internal/bookings/{own_booking['booking_id']}", headers=headers
        )
        other = await client.get(
            f"/api/v1/internal/bookings/{other_booking['booking_id']}", headers=headers
        )
        mutation = await client.post(
            f"/api/v1/internal/bookings/{own_booking['booking_id']}/transition",
            headers=headers,
            json={"target_status": "cancelled", "note": "attempted by staff"},
        )
        assignment = await client.put(
            f"/api/v1/internal/bookings/{own_booking['booking_id']}/assignment",
            headers=headers,
            json={"staff_id": "staff_q7_other"},
        )
        fleet = await client.get("/api/v1/internal/vehicles", headers=headers)
        users = await client.get("/api/v1/internal/users", headers=headers)

        assert own.status_code == 200
        assert own.json()["assigned_staff_id"] == "staff_q7"
        assert own.json()["customer_profile"]["summary"]["total_bookings"] == 1
        assert other.status_code == 404
        assert mutation.status_code == 403
        assert assignment.status_code == 403
        assert fleet.status_code == 403
        assert users.status_code == 403
    finally:
        app.dependency_overrides.pop(get_internal_portal_service, None)


@pytest.mark.asyncio
async def test_manager_api_manages_only_its_showroom_and_cannot_use_admin_commands(
    client, booking_db, catalog, confirmed_booking_factory
):
    _seed_staff(booking_db, catalog)
    own_booking = confirmed_booking_factory(catalog["slot_main"])
    foreign_booking = confirmed_booking_factory(catalog["slot_gv"])
    service = InternalPortalService(booking_db, now=lambda: FIXED_NOW)
    headers = _headers(
        service,
        username="manager.routes",
        role="showroom_manager",
        showroom_ids=[catalog["showroom_q7"]],
    )
    app.dependency_overrides[get_internal_portal_service] = lambda: service
    try:
        own = await client.get(
            f"/api/v1/internal/bookings/{own_booking['booking_id']}", headers=headers
        )
        foreign = await client.get(
            f"/api/v1/internal/bookings/{foreign_booking['booking_id']}", headers=headers
        )
        assigned = await client.put(
            f"/api/v1/internal/bookings/{own_booking['booking_id']}/assignment",
            headers=headers,
            json={"staff_id": "staff_q7"},
        )
        cross_scope_action = await client.post(
            f"/api/v1/internal/bookings/{foreign_booking['booking_id']}/transition",
            headers=headers,
            json={"target_status": "cancelled"},
        )
        shift = await client.post(
            "/api/v1/internal/shifts",
            headers=headers,
            json={
                "staff_id": "staff_q7_other",
                "showroom_id": catalog["showroom_q7"],
                "start_at": (catalog["primary_start"] + timedelta(days=1)).isoformat(),
                "end_at": (catalog["primary_start"] + timedelta(days=1, hours=4)).isoformat(),
            },
        )
        shifted = await client.patch(
            f"/api/v1/internal/shifts/{shift.json()['id']}",
            headers=headers,
            json={"end_at": (catalog["primary_start"] + timedelta(days=1, hours=5)).isoformat()},
        )
        transfer = await client.post(
            "/api/v1/internal/vehicles/demo_main/transfer",
            headers=headers,
            json={
                "to_showroom_id": catalog["showroom_gv"],
                "effective_at": (FIXED_NOW + timedelta(hours=1)).isoformat(),
            },
        )
        catalog_change = await client.post(
            "/api/v1/internal/catalog/models",
            headers=headers,
            json={"code": "VF9", "name": "VinFast VF 9", "vehicle_type": "SUV"},
        )

        assert own.status_code == 200
        assert own.json()["customer_profile"]["summary"]["total_bookings"] == 1
        assert foreign.status_code == 404
        assert assigned.status_code == 200
        assert assigned.json()["assigned_staff_id"] == "staff_q7"
        assert cross_scope_action.status_code == 403
        assert shift.status_code == 201
        assert shifted.status_code == 200
        assert transfer.status_code == 403
        assert catalog_change.status_code == 403
    finally:
        app.dependency_overrides.pop(get_internal_portal_service, None)


@pytest.mark.asyncio
async def test_admin_transfer_validates_booking_conflict_and_writes_audit(
    client, booking_db, catalog, confirmed_booking_factory
):
    conflicting_booking = confirmed_booking_factory(catalog["slot_main"])
    service = InternalPortalService(booking_db, now=lambda: FIXED_NOW)
    headers = _headers(service, username="admin.routes", role="operations_admin")
    app.dependency_overrides[get_internal_portal_service] = lambda: service
    try:
        valid = await client.post(
            "/api/v1/internal/vehicles/demo_gv/transfer",
            headers=headers,
            json={
                "to_showroom_id": catalog["showroom_q7"],
                "effective_at": (FIXED_NOW + timedelta(hours=1)).isoformat(),
            },
        )
        conflict = await client.post(
            "/api/v1/internal/vehicles/demo_main/transfer",
            headers=headers,
            json={
                "to_showroom_id": catalog["showroom_gv"],
                "effective_at": (FIXED_NOW + timedelta(hours=1)).isoformat(),
            },
        )
        audit = await client.get("/api/v1/internal/audit-events", headers=headers)
        moved = await client.get(
            "/api/v1/internal/vehicles", headers=headers, params={"showroom_id": catalog["showroom_q7"]}
        )

        assert valid.status_code == 201
        assert conflict.status_code == 409
        assert conflict.json()["detail"]["code"] == "FUTURE_SCHEDULE_EXISTS"
        assert audit.status_code == 200
        assert "vehicle.transferred" in {item["action"] for item in audit.json()}
        assert "demo_gv" in {item["id"] for item in moved.json()}
        assert conflicting_booking["booking_id"]
        with booking_db.connect() as connection:
            source_slot = connection.execute(
                "SELECT status,block_reason FROM test_drive_slots WHERE id=?", (catalog["slot_gv"],)
            ).fetchone()
        assert source_slot["status"] == "blocked"
        assert source_slot["block_reason"].startswith("vehicle_transfer:")
    finally:
        app.dependency_overrides.pop(get_internal_portal_service, None)
