import pytest
import src.api.routes as routes_module
from src.services.booking.public_invitation import PublicInvitation


@pytest.mark.asyncio
async def test_public_invitation_endpoint_returns_personalised_booking(client, monkeypatch):
    invitation = PublicInvitation(
        guest_name="Nguyễn Hoàng Minh",
        start_at="2026-08-28T02:30:00+00:00",
        vehicle_id="vf9",
        model="VinFast VF 9 Plus",
        showroom="VinFast Landmark 81",
        address="208 Nguyễn Hữu Cảnh, TP.HCM",
        booking_code="VF260828A47C3D",
    )
    monkeypatch.setattr(routes_module.public_invitation_service, "resolve", lambda _token: invitation)

    response = await client.get("/api/v1/invitations/v1.payload.signature")

    assert response.status_code == 200
    assert response.json() == {"data": invitation.as_dict()}


@pytest.mark.asyncio
async def test_public_invitation_endpoint_hides_invalid_capability(client, monkeypatch):
    def invalid(_token):
        raise KeyError("INVITATION_INVALID")

    monkeypatch.setattr(routes_module.public_invitation_service, "resolve", invalid)

    response = await client.get("/api/v1/invitations/v1.invalid.signature")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "INVITATION_UNAVAILABLE"
