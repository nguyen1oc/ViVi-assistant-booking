# ruff: noqa: E402
#
# LangSmith must be configured before importing graph/routes so LangChain and
# LangGraph receive the canonical LANGSMITH_* variables during initialization.
import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from src.config import get_settings
from src.observability import configure_langsmith

settings = get_settings()
configure_langsmith(settings)

from src.agents.graph import close_persistent_agent, initialize_persistent_agent
from src.api.routes import router
from src.api.site_routes import router as site_router
from src.bootstrap import initialize_database
from src.dependencies import booking_service, database, zalo_client
from src.internal_portal.errors import InternalPortalError
from src.internal_portal.routes import router as internal_router
from src.logging_config import configure_logging
from src.security.rate_limit import RateLimitMiddleware
from src.services.zalo_bot import ZaloPollingService


def _warn_on_development_secrets(settings) -> None:
    """Hét lên khi ứng dụng đang chạy bằng khoá dự phòng nằm sẵn trong mã nguồn.

    Chốt chặn ở Settings.require_production_otp_secret chỉ bật khi APP_ENV được
    đặt đúng bằng "production". Quên đặt biến đó lúc triển khai là mất im lặng cả
    bốn lớp bảo vệ, và ba khoá ký sẽ rơi về hằng số ai đọc repo cũng biết. Không
    có cách nào để mã tự nhận ra mình đang chạy thật hay chạy máy cá nhân, nên
    thứ duy nhất làm được là để lại một dòng log không thể bỏ sót.
    """
    if settings.app_env == "production":
        return
    missing = [
        name
        for name, value in (
            ("BOOKING_ACCESS_OTP_SECRET", settings.booking_access_otp_secret),
            ("CONVERSATION_SIGNING_SECRET", settings.conversation_signing_secret),
        )
        if not value
    ]
    if not missing:
        return
    logging.getLogger(__name__).warning(
        "INSECURE STARTUP: APP_ENV=%s and %s not set, so signing keys fall back to "
        "constants published in this repository. Anyone can forge booking invitation "
        "links and OTP material. Never serve public traffic in this state: set "
        "APP_ENV=production and provide the secrets.",
        settings.app_env,
        " and ".join(missing),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    initialize_database(database, settings)
    await initialize_persistent_agent(
        settings.database_url,
        required=settings.app_env == "production",
    )
    logging.getLogger(__name__).info("Starting %s in %s mode", settings.app_name, settings.app_env)
    _warn_on_development_secrets(settings)
    polling_task = None
    notification_task = None
    if settings.zalo_bot_enabled and settings.zalo_bot_polling_enabled and zalo_client:
        polling_task = asyncio.create_task(
            ZaloPollingService(
                database,
                zalo_client,
                settings.zalo_bot_poll_timeout_seconds,
                settings.zalo_bot_processed_message_retention_days,
            ).run()
        )
        logging.getLogger(__name__).info("Zalo Bot polling enabled")

    async def dispatch_notifications() -> None:
        while True:
            try:
                expired_holds = await asyncio.to_thread(booking_service.expire_held_bookings)
                if expired_holds:
                    logging.getLogger(__name__).info("Released %s expired booking holds", expired_holds)
                await asyncio.to_thread(
                    booking_service.dispatch_due_notifications,
                    settings.notification_batch_size,
                    settings.notification_processing_timeout_seconds,
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                logging.getLogger(__name__).exception("Notification dispatch failed")
            await asyncio.sleep(settings.notification_poll_interval_seconds)

    notification_task = asyncio.create_task(dispatch_notifications())
    yield
    if polling_task:
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass
    if notification_task:
        notification_task.cancel()
        try:
            await notification_task
        except asyncio.CancelledError:
            pass
    await close_persistent_agent()
    logging.getLogger(__name__).info("Shutting down")


app = FastAPI(
    title="AI20K Agent",
    description="AI Agent built with LangGraph",
    version="1.0.0",
    lifespan=lifespan,
)

media_root = Path(settings.media_root).resolve()
media_root.mkdir(parents=True, exist_ok=True)
cors_list = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Content-Length",
        "Accept",
        "Origin",
        "User-Agent",
        "Cache-Control",
        "X-Requested-With",
        "X-Trace-Id",
        "X-Conversation-Id",
        "X-Session-Id",
        "If-Match",
        "If-None-Match",
    ],
)
app.add_middleware(RateLimitMiddleware, database=database, settings=settings)


@app.exception_handler(InternalPortalError)
async def internal_portal_error_handler(_request, exc: InternalPortalError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": {"code": exc.code, "message": str(exc)}},
    )


@app.middleware("http")
async def request_logging(request, call_next):
    started = time.perf_counter()
    is_chat_request = request.url.path == "/api/v1/chat" or (
        request.url.path.startswith("/api/v1/driver-chat/") and request.url.path.endswith("/chat")
    )
    trace_id = str(uuid.uuid4()) if is_chat_request else ""
    if trace_id:
        request.state.trace_id = trace_id
    try:
        response = await call_next(request)
        duration_ms = (time.perf_counter() - started) * 1000
        logging.getLogger("http").info(
            "%s %s -> %s %.1fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
    except Exception:
        logging.getLogger("http").exception("Unhandled error: %s %s", request.method, request.url.path)
        raise


app.include_router(router, prefix="/api/v1")
app.include_router(site_router, prefix="/api/v1")
app.include_router(internal_router, prefix="/api/v1")
app.mount("/media", StaticFiles(directory=media_root), name="media")


@app.get("/api/v1/echo")
async def echo(text: str = "Hello") -> dict[str, str]:
    return {
        "status": "ok",
        "echo": text,
        "time": datetime.now(UTC).isoformat(),
    }


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.app_env}
