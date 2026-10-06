import re

from src.services.booking.public_invitation import (
    PublicInvitationService,
    PublicInvitationTokenManager,
)


def test_public_invitation_token_is_stable_unique_and_tamper_evident():
    manager = PublicInvitationTokenManager("test-public-invitation-secret")

    first = manager.issue("VF260821A47C3D")
    repeated = manager.issue("VF260821A47C3D")
    second = manager.issue("VF260821B88F2E")

    assert first == repeated
    assert first != second
    assert manager.verify(first) == "VF260821A47C3D"
    assert manager.verify(first[:-1] + ("A" if first[-1] != "A" else "B")) is None


def test_invitation_link_follows_active_booking_across_reschedule(
    booking_service,
    booking_db,
    access_factory,
    catalog,
):
    manager = PublicInvitationTokenManager("test-public-invitation-secret")
    invitations = PublicInvitationService(booking_db, manager)
    access = access_factory("reschedule")
    old_booking_id = access["booking"]["booking_id"]
    booking_code = access["booking"]["confirmed"]["booking_code"]
    token = manager.issue(booking_code)

    original = invitations.resolve(token)
    with booking_db.connect() as connection:
        recipient_id = connection.execute(
            "SELECT driver_person_id FROM bookings WHERE id=?",
            (old_booking_id,),
        ).fetchone()["driver_person_id"]
    confirmation_email = booking_service._render_notification(
        old_booking_id,
        "booking_confirmation",
        recipient_id,
    )
    held = booking_service.hold_reschedule_slot(
        old_booking_id,
        catalog["slot_later"],
        access["session"]["access_session_token"],
        "reschedule-hold:invitation-link",
    )
    booking_service.confirm_reschedule(
        old_booking_id,
        held["booking_id"],
        access["session"]["access_session_token"],
        "reschedule-confirm:invitation-link",
    )
    updated = invitations.resolve(token)
    reschedule_email = booking_service._render_notification(
        held["booking_id"],
        "reschedule_confirmation",
        recipient_id,
    )
    invitation_pattern = r'href="([^"]+/invitation/v1\.[^"]+)"'
    confirmation_link = re.search(invitation_pattern, confirmation_email.html)
    reschedule_link = re.search(invitation_pattern, reschedule_email.html)

    assert original.booking_code == updated.booking_code == booking_code
    assert original.start_at != updated.start_at
    assert updated.start_at == catalog["primary_start"].replace(hour=catalog["primary_start"].hour + 2).isoformat()
    assert updated.guest_name == "Huynh Thi Hai Chau"
    assert updated.vehicle_id == "vf6"
    assert updated.model == "VinFast VF 6 Plus"
    assert confirmation_link is not None
    assert reschedule_link is not None
    assert confirmation_link.group(1) == reschedule_link.group(1)


def test_invitation_is_unavailable_after_cancellation(
    booking_service,
    booking_db,
    access_factory,
):
    manager = PublicInvitationTokenManager("test-public-invitation-secret")
    invitations = PublicInvitationService(booking_db, manager)
    access = access_factory("cancel")
    booking_code = access["booking"]["confirmed"]["booking_code"]
    token = manager.issue(booking_code)

    booking_service.cancel_booking(
        access["booking"]["booking_id"],
        access["session"]["access_session_token"],
        "cancel:public-invitation",
    )

    try:
        invitations.resolve(token)
    except KeyError as error:
        assert error.args == ("INVITATION_UNAVAILABLE",)
    else:
        raise AssertionError("A cancelled booking must not expose an active invitation")
