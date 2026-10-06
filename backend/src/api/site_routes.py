import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import JSONResponse

from src.models.site import ContentDocument, DataEnvelope, ErrorEnvelope, VehicleDetail, VehicleSummary
from src.services.site_catalog import site_catalog_service

router = APIRouter()
_CACHE_CONTROL = "public, max-age=300, stale-while-revalidate=86400"


def _meta(request_id: str) -> dict[str, str]:
    return {"requestId": request_id, "serverTime": datetime.now(UTC).isoformat()}


def _error(code: str, message: str, status: int, request_id: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message, "retryable": False, "details": {}}, "meta": _meta(request_id)})


def _result(request: Request, data: Any, request_id: str) -> Response:
    payload = {"data": data, "meta": _meta(request_id)}
    etag = site_catalog_service.etag(data)
    headers = {"ETag": etag, "Cache-Control": _CACHE_CONTROL, "X-Request-ID": request_id}
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=headers)
    return JSONResponse(content=payload, headers=headers)


@router.get("/vehicles", response_model=DataEnvelope[list[VehicleSummary]], responses={422: {"model": ErrorEnvelope}})
async def list_vehicles(
    request: Request,
    category: str | None = Query(default=None, pattern="^(personal|fleet)$"),
    featured: bool | None = None,
    test_drive_eligible: bool | None = Query(default=None, alias="testDriveEligible"),
    limit: int = Query(default=20, ge=1, le=50),
) -> Response:
    request_id = request.headers.get("x-request-id") or f"req_{uuid.uuid4().hex}"
    data = site_catalog_service.list_vehicles(category=category, featured=featured, test_drive_eligible=test_drive_eligible, limit=limit)
    return _result(request, data, request_id)


@router.get("/vehicles/{vehicle_id}", response_model=DataEnvelope[VehicleDetail], responses={404: {"model": ErrorEnvelope}})
async def get_vehicle(vehicle_id: str, request: Request) -> Response:
    request_id = request.headers.get("x-request-id") or f"req_{uuid.uuid4().hex}"
    data = site_catalog_service.get_vehicle(vehicle_id)
    if data is None:
        return _error("VEHICLE_NOT_FOUND", "Không tìm thấy mẫu xe.", 404, request_id)
    return _result(request, data, request_id)


@router.get("/content/{page}", response_model=DataEnvelope[ContentDocument], responses={404: {"model": ErrorEnvelope}})
async def get_content(page: str, request: Request) -> Response:
    request_id = request.headers.get("x-request-id") or f"req_{uuid.uuid4().hex}"
    data = site_catalog_service.get_content(page)
    if data is None:
        return _error("CONTENT_NOT_FOUND", "Không tìm thấy nội dung.", 404, request_id)
    return _result(request, data, request_id)
