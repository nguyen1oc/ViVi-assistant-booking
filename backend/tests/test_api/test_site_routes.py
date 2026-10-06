import pytest


@pytest.mark.asyncio
async def test_vehicle_list_uses_contract_envelope_filters_and_cache(client):
    response = await client.get("/api/v1/vehicles", params={"category": "fleet", "testDriveEligible": "false", "limit": 1})
    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 1
    assert body["data"][0]["category"] == "fleet"
    assert body["data"][0]["testDriveEligible"] is False
    assert body["meta"]["requestId"].startswith("req_")
    assert response.headers["cache-control"].startswith("public, max-age=300")

    cached = await client.get("/api/v1/vehicles", params={"category": "fleet", "testDriveEligible": "false", "limit": 1}, headers={"If-None-Match": response.headers["etag"]})
    assert cached.status_code == 304
    assert not cached.content


@pytest.mark.asyncio
async def test_vehicle_detail_and_not_found(client):
    response = await client.get("/api/v1/vehicles/vf7")
    assert response.status_code == 200
    vehicle = response.json()["data"]
    assert vehicle["id"] == "vf7"
    assert "specifications" in vehicle
    assert "gallery" in vehicle

    missing = await client.get("/api/v1/vehicles/unknown")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "VEHICLE_NOT_FOUND"


@pytest.mark.asyncio
@pytest.mark.parametrize("page", ["home", "charging", "after-sales"])
async def test_content_pages(page, client):
    response = await client.get(f"/api/v1/content/{page}")
    assert response.status_code == 200
    assert response.json()["data"]["revision"]
    assert response.headers["etag"]


@pytest.mark.asyncio
async def test_vehicle_query_validation(client):
    assert (await client.get("/api/v1/vehicles", params={"limit": 51})).status_code == 422
    assert (await client.get("/api/v1/vehicles", params={"category": "invalid"})).status_code == 422
