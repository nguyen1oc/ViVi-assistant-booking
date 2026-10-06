from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from src.api import routes as routes_module


@pytest.mark.asyncio
@pytest.mark.parametrize("app_env", ["development", "production"])
@pytest.mark.parametrize("enabled", [False, True])
async def test_floating_demo_capability_follows_server_flag(client, monkeypatch, app_env, enabled):
    monkeypatch.setattr(
        routes_module,
        "get_settings",
        lambda: SimpleNamespace(app_env=app_env, floating_demo_enabled=enabled),
    )

    response = await client.get("/api/v1/floating-demo/capabilities")

    assert response.status_code == 200
    assert response.json()["enabled"] is enabled


@pytest.mark.asyncio
@pytest.mark.parametrize("app_env", ["development", "production"])
@pytest.mark.parametrize("enabled", [False, True])
async def test_floating_demo_options_follows_server_flag(client, monkeypatch, app_env, enabled):
    monkeypatch.setattr(
        routes_module,
        "get_settings",
        lambda: SimpleNamespace(app_env=app_env, floating_demo_enabled=enabled),
    )
    availability = {"showrooms": [{"id": "showroom-1"}], "slots": []}
    search = Mock(return_value=availability)
    # Expose only the search operation: demo must not hold or confirm a booking.
    monkeypatch.setattr(routes_module, "booking_service", SimpleNamespace(search_options=search))

    response = await client.post(
        "/api/v1/floating-demo/options",
        json={"vehicle_model": "VF 9", "latitude": 10.77, "longitude": 106.70},
    )

    if enabled:
        assert response.status_code == 200
        assert response.json() == {"success": True, "data": availability}
        search.assert_called_once_with(
            vehicle_model="VF 9", showroom_id=None, showroom_query=None,
            showroom_limit=12, latitude=10.77, longitude=106.70,
        )
    else:
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "FLOATING_DEMO_DISABLED"
        search.assert_not_called()


@pytest.mark.asyncio
async def test_production_demo_still_enforces_guardrails(client, monkeypatch):
    monkeypatch.setattr(
        routes_module, "get_settings",
        lambda: SimpleNamespace(app_env="production", floating_demo_enabled=True),
    )
    guardrails = Mock()
    guardrails.inspect_demo_action.return_value = SimpleNamespace(
        allowed=False, code="INVALID_INPUT", user_message="Invalid demo input",
    )
    monkeypatch.setattr(routes_module, "get_guardrails", lambda: guardrails)
    search = Mock()
    monkeypatch.setattr(routes_module, "booking_service", SimpleNamespace(search_options=search))

    response = await client.post("/api/v1/floating-demo/options", json={"vehicle_model": "VF 9"})

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_INPUT"
    guardrails.inspect_demo_action.assert_called_once()
    search.assert_not_called()


@pytest.mark.asyncio
async def test_removed_demo_confirmation_endpoint_cannot_bypass_otp(client, monkeypatch):
    monkeypatch.setattr(
        routes_module, "get_settings",
        lambda: SimpleNamespace(app_env="production", floating_demo_enabled=True),
    )
    response = await client.post(
        "/api/v1/floating-demo/confirm",
        json={"booking_id": "booking-1", "expected_version": 1, "ui_action_id": "demo-confirm-1"},
    )

    assert response.status_code == 404
