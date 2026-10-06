from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from src.config import Settings
from src.database import Database
from src.security.client_identity import ClientIdentity, get_or_create_identity


@dataclass(frozen=True, slots=True)
class RateLimitRule:
    key: str
    limit: int
    window_seconds: int


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int = 0
    rule_key: str = ""


class _RateLimitRejectedError(RuntimeError):
    def __init__(self, decision: RateLimitDecision) -> None:
        super().__init__(decision.rule_key)
        self.decision = decision


def consume_rate_limit_counter(
    connection,
    *,
    bucket_key: str,
    limit: int,
    window_seconds: int,
    now: datetime | None = None,
) -> RateLimitDecision:
    """Atomically consume one request from a fixed-window bucket."""
    now = now or datetime.now(UTC)
    window_epoch = int(now.timestamp() // window_seconds * window_seconds)
    window_start = datetime.fromtimestamp(window_epoch, UTC)
    expires_at = window_start + timedelta(seconds=window_seconds)
    retry_after = max(1, int((expires_at - now).total_seconds()))
    row = connection.execute(
        "INSERT INTO rate_limit_counters("
        "bucket_key,window_start,expires_at,count,created_at,updated_at"
        ") VALUES(?,?,?,?,?,?) "
        "ON CONFLICT(bucket_key,window_start) DO UPDATE SET "
        "count=rate_limit_counters.count+1,expires_at=excluded.expires_at,updated_at=excluded.updated_at "
        "RETURNING count",
        (
            bucket_key,
            window_start.isoformat(),
            expires_at.isoformat(),
            1,
            now.isoformat(),
            now.isoformat(),
        ),
    ).fetchone()
    count = int(row["count"] if row else 1)
    if count > limit:
        return RateLimitDecision(False, retry_after_seconds=retry_after, rule_key=bucket_key)
    return RateLimitDecision(True)


class PostgresRateLimitStore:
    def __init__(self, database: Database) -> None:
        self.database = database

    def check(self, *, bucket_key: str, limit: int, window_seconds: int) -> RateLimitDecision:
        return self.check_many([RateLimitRule(bucket_key, limit, window_seconds)])

    def check_many(self, rules: list[RateLimitRule]) -> RateLimitDecision:
        """Consume all rules together so a rejected request does not partially spend quota."""
        now = datetime.now(UTC)
        try:
            with self.database.transaction(immediate=True) as connection:
                for rule in rules:
                    decision = consume_rate_limit_counter(
                        connection,
                        bucket_key=rule.key,
                        limit=rule.limit,
                        window_seconds=rule.window_seconds,
                        now=now,
                    )
                    if not decision.allowed:
                        raise _RateLimitRejectedError(decision)
        except _RateLimitRejectedError as exc:
            return exc.decision
        return RateLimitDecision(True)


def route_class_for_path(path: str) -> str | None:
    if path == "/api/v1/chat":
        return "chat"
    if path in {"/api/v1/demo/action", "/api/v1/test-drive/actions"}:
        return "demo_action"
    # Endpoint thiệp mời không cần đăng nhập và nhận token tuỳ ý trên URL, nên nếu
    # không chặn thì có thể dò mã lịch không giới hạn.
    if path.startswith("/api/v1/invitations/"):
        return "invitation"
    return None


def rules_for_route(route_class: str, identity: ClientIdentity, settings: Settings) -> list[RateLimitRule]:
    if route_class == "invitation":
        # Chỉ khoá theo IP. Người nhận thiệp thường chưa có phiên nào trên site.
        return [
            RateLimitRule(
                f"invitation:ip:minute:{identity.client_ip}",
                settings.rate_limit_invitation_per_ip_per_minute,
                60,
            ),
            RateLimitRule(
                f"invitation:ip:hour:{identity.client_ip}",
                settings.rate_limit_invitation_per_ip_per_hour,
                3_600,
            ),
        ]
    if route_class == "chat":
        return [
            RateLimitRule(
                f"chat:session:minute:{identity.session_id}",
                settings.rate_limit_chat_per_session_per_minute,
                60,
            ),
            RateLimitRule(
                f"chat:session:hour:{identity.session_id}",
                settings.rate_limit_chat_per_session_per_hour,
                3_600,
            ),
            RateLimitRule(f"chat:ip:minute:{identity.client_ip}", settings.rate_limit_chat_per_ip_per_minute, 60),
            RateLimitRule(f"chat:ip:hour:{identity.client_ip}", settings.rate_limit_chat_per_ip_per_hour, 3_600),
        ]
    if route_class == "demo_action":
        return [
            RateLimitRule(
                f"demo_action:session:minute:{identity.session_id}",
                settings.rate_limit_demo_action_per_session_per_minute,
                60,
            ),
            RateLimitRule(
                f"demo_action:session:hour:{identity.session_id}",
                settings.rate_limit_demo_action_per_session_per_hour,
                3_600,
            ),
            RateLimitRule(
                f"demo_action:ip:minute:{identity.client_ip}",
                settings.rate_limit_demo_action_per_ip_per_minute,
                60,
            ),
            RateLimitRule(
                f"demo_action:ip:hour:{identity.client_ip}",
                settings.rate_limit_demo_action_per_ip_per_hour,
                3_600,
            ),
        ]
    return []


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, database: Database, settings: Settings) -> None:
        super().__init__(app)
        self.settings = settings
        self.store = PostgresRateLimitStore(database)

    async def dispatch(self, request: Request, call_next) -> Response:
        identity = get_or_create_identity(request, self.settings)
        request.state.client_identity = identity
        route_class = route_class_for_path(request.url.path)
        decision = RateLimitDecision(True)
        if self.settings.rate_limit_enabled and route_class:
            decision = self.store.check_many(rules_for_route(route_class, identity, self.settings))

        if decision.allowed:
            response = await call_next(request)
        else:
            response = JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Bạn gửi hơi nhanh, vui lòng thử lại sau.",
                        "retryable": True,
                        "details": {"retry_after_seconds": decision.retry_after_seconds},
                    }
                },
                headers={"Retry-After": str(decision.retry_after_seconds)},
            )

        if identity.is_new_session:
            response.set_cookie(
                self.settings.rate_limit_anon_cookie_name,
                identity.session_id,
                max_age=self.settings.rate_limit_anon_cookie_ttl_seconds,
                httponly=True,
                samesite="none" if self.settings.app_env == "production" else "lax",
                secure=self.settings.app_env == "production",
            )
        return response
