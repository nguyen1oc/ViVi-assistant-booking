import pytest
from src.internal_portal import InternalPortalService
from src.internal_portal.routes import get_internal_portal_service
from src.main import app


@pytest.mark.asyncio
async def test_internal_login_me_and_dashboard(client, booking_db, catalog):
    service = InternalPortalService(booking_db)
    service.create_user(
        username="ops.test",
        password="StrongPortal!2026",
        display_name="Operations Test",
        role="operations_admin",
    )
    app.dependency_overrides[get_internal_portal_service] = lambda: service
    try:
        response = await client.post(
            "/api/v1/internal/auth/login",
            json={"username": "ops.test", "password": "StrongPortal!2026"},
        )
        assert response.status_code == 200
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        me = await client.get("/api/v1/internal/me", headers=headers)
        dashboard = await client.get("/api/v1/internal/dashboard", headers=headers)

        assert me.status_code == 200
        assert me.json()["role"] == "operations_admin"
        assert dashboard.status_code == 200
        assert dashboard.json()["showroom_total"] == 3
        assert dashboard.json()["active_showroom_total"] == 2

        weak_password = await client.post(
            "/api/v1/internal/users",
            headers=headers,
            json={
                "username": "manager.weak",
                "password": "1234567",
                "display_name": "Weak Manager",
                "role": "showroom_manager",
                "showroom_ids": [catalog["showroom_q7"]],
            },
        )
        assert weak_password.status_code == 422

        created_user = await client.post(
            "/api/v1/internal/users",
            headers=headers,
            json={
                "username": "manager.web",
                "password": "12345678",
                "display_name": "Manager Web",
                "role": "showroom_manager",
                "showroom_ids": [catalog["showroom_q7"]],
            },
        )
        users = await client.get("/api/v1/internal/users", headers=headers)

        assert created_user.status_code == 201
        assert created_user.json()["username"] == "manager.web"
        assert "password" not in created_user.json()
        assert users.status_code == 200
        assert {item["username"] for item in users.json()} == {"ops.test", "manager.web"}

        updated_user = await client.patch(
            f"/api/v1/internal/users/{created_user.json()['id']}",
            headers=headers,
            json={"display_name": "Manager Web Updated", "is_active": False},
        )
        assert updated_user.status_code == 200
        assert updated_user.json()["display_name"] == "Manager Web Updated"
        assert updated_user.json()["is_active"] is False

        blocked_import = await client.post(
            "/api/v1/admin/import/eval-dataset",
            headers=headers,
            json={"files": {"seed/12_internal_users.csv": "id,username"}},
        )
        assert blocked_import.status_code == 422
        assert blocked_import.json()["detail"]["code"] == "SECURITY_STATE_IMPORT_FORBIDDEN"
    finally:
        app.dependency_overrides.pop(get_internal_portal_service, None)


@pytest.mark.asyncio
async def test_internal_endpoint_rejects_missing_session(client):
    response = await client.get("/api/v1/internal/dashboard")
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "AUTH_REQUIRED"

    legacy_dashboard = await client.get("/api/v1/dashboard")
    admin_import = await client.post("/api/v1/admin/import/showrooms", json={"csv_text": "id,code"})
    assert legacy_dashboard.status_code == 404
    assert admin_import.status_code == 401
