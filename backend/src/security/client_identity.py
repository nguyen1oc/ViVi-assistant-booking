from __future__ import annotations

import re
import secrets
from dataclasses import dataclass

from fastapi import Request

from src.config import Settings

_ANON_SESSION_RE = re.compile(r"^[A-Za-z0-9_-]{32,64}$")


@dataclass(frozen=True, slots=True)
class ClientIdentity:
    session_id: str
    client_ip: str
    is_new_session: bool = False


def get_client_ip(request: Request, settings: Settings) -> str:
    if settings.rate_limit_trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",", 1)[0].strip() or "unknown"
        real_ip = request.headers.get("x-real-ip", "")
        if real_ip:
            return real_ip.strip() or "unknown"
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def get_or_create_identity(request: Request, settings: Settings) -> ClientIdentity:
    cookie_name = settings.rate_limit_anon_cookie_name
    session_id = (request.cookies.get(cookie_name) or "").strip()
    if _ANON_SESSION_RE.fullmatch(session_id):
        return ClientIdentity(session_id=session_id, client_ip=get_client_ip(request, settings))
    return ClientIdentity(
        session_id=secrets.token_urlsafe(32),
        client_ip=get_client_ip(request, settings),
        is_new_session=True,
    )
