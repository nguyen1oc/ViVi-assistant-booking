import pytest
from src.internal_portal import InternalPortalError, InternalPortalService


def _principal(service, *, username, role, staff_id=None, showroom_ids=None):
    password = "1234512345"
    user = service.create_user(
        username=username,
        password=password,
        display_name=username,
        role=role,
        staff_id=staff_id,
        showroom_ids=showroom_ids or [],
    )
    token = service.login(username, password)["access_token"]
    return user, service.authenticate(token)


def test_confirmed_booking_notifies_assigned_staff_and_showroom_manager(
    booking_db,
    booking_service,
    catalog,
    ready_draft_factory,
):
    created = "2026-08-03T02:00:00+00:00"
    with booking_db.transaction(immediate=True) as connection:
        connection.execute(
            "INSERT INTO sales_staff("
            "id,showroom_id,employee_code,full_name,phone,email,role,status,is_active,created_at,updated_at"
            ") VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                "staff_notification",
                catalog["showroom_q7"],
                "NOTIFY-Q7",
                "Notification Staff",
                "0901000099",
                "notification.staff@example.test",
                "sales_consultant",
                "active",
                1,
                created,
                created,
            ),
        )
        connection.execute(
            "INSERT INTO slot_sales_assignments("
            "id,slot_id,sales_staff_id,assignment_role,status,created_at,updated_at"
            ") VALUES(?,?,?,?,?,?,?)",
            (
                "assignment_notification",
                catalog["slot_main"],
                "staff_notification",
                "test_drive_consultant",
                "assigned",
                created,
                created,
            ),
        )

    portal = InternalPortalService(booking_db)
    staff_user, staff = _principal(
        portal,
        username="staff.notification",
        role="staff",
        staff_id="staff_notification",
    )
    manager_user, manager = _principal(
        portal,
        username="manager.notification",
        role="showroom_manager",
        showroom_ids=[catalog["showroom_q7"]],
    )
    _, other_manager = _principal(
        portal,
        username="manager.other",
        role="showroom_manager",
        showroom_ids=[catalog["showroom_gv"]],
    )

    prepared = ready_draft_factory()
    confirmed = booking_service.confirm_booking(
        prepared["booking_id"],
        "confirm:internal-notifications",
        prepared["draft"]["version"],
    )

    staff_feed = portal.list_notifications(staff)
    manager_feed = portal.list_notifications(manager)
    assert staff_feed["unread_count"] == 1
    assert manager_feed["unread_count"] == 1
    assert portal.list_notifications(other_manager) == {"items": [], "unread_count": 0}
    assert staff_feed["items"][0]["booking_id"] == prepared["booking_id"]
    assert confirmed["booking_code"] in staff_feed["items"][0]["title"]
    assert confirmed["advisor"] == {
        "id": "staff_notification",
        "full_name": "Notification Staff",
        "phone": "0901000099",
    }
    assert manager_feed["items"][0]["showroom_id"] == catalog["showroom_q7"]

    with booking_db.connect() as connection:
        recipients = {
            row["recipient_user_id"]
            for row in connection.execute(
                "SELECT recipient_user_id FROM internal_notifications WHERE booking_id=?",
                (prepared["booking_id"],),
            )
        }
    assert recipients == {staff_user["id"], manager_user["id"]}

    with pytest.raises(InternalPortalError) as error:
        portal.mark_notification_read(manager, staff_feed["items"][0]["id"])
    assert error.value.code == "NOTIFICATION_NOT_FOUND"

    portal.mark_notification_read(staff, staff_feed["items"][0]["id"])
    assert portal.list_notifications(staff)["unread_count"] == 0
    result = portal.mark_all_notifications_read(manager)
    assert result["updated"] == 1
    assert portal.list_notifications(manager, unread_only=True)["items"] == []
