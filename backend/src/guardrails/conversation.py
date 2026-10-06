from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache

from src.config import get_settings

_TOKEN_VERSION = "v1"
_DEVELOPMENT_SECRET = secrets.token_bytes(32)


@dataclass(frozen=True, slots=True)
class ConversationIdentity:
    public_token: str
    thread_id: str


class ConversationTokenManager:
    """Issue and verify opaque, tamper-evident conversation capabilities."""

    def __init__(
        self,
        secret: str | bytes,
        *,
        ttl_seconds: int,
        now: Callable[[], float] = time.time,
    ) -> None:
        encoded = secret.encode("utf-8") if isinstance(secret, str) else secret
        if len(encoded) < 32:
            raise ValueError("conversation signing secret must contain at least 32 bytes")
        self._secret = encoded
        self._ttl_seconds = ttl_seconds
        self._now = now

    def issue(self) -> ConversationIdentity:
        issued_at = int(self._now())
        nonce = secrets.token_hex(16)
        payload = f"{_TOKEN_VERSION}.{issued_at:x}.{nonce}"
        signature = self._signature(payload)
        return ConversationIdentity(
            public_token=f"{payload}.{signature}",
            thread_id=f"conversation:{nonce}",
        )

    def verify(self, token: str) -> ConversationIdentity | None:
        try:
            version, issued_hex, nonce, signature = token.split(".")
            issued_at = int(issued_hex, 16)
        except (AttributeError, TypeError, ValueError):
            return None
        if version != _TOKEN_VERSION or len(nonce) != 32:
            return None
        try:
            bytes.fromhex(nonce)
        except ValueError:
            return None
        payload = f"{version}.{issued_hex}.{nonce}"
        if not hmac.compare_digest(signature, self._signature(payload)):
            return None
        age = int(self._now()) - issued_at
        if age < 0 or age > self._ttl_seconds:
            return None
        return ConversationIdentity(public_token=token, thread_id=f"conversation:{nonce}")

    def _signature(self, payload: str) -> str:
        digest = hmac.new(self._secret, payload.encode("ascii"), hashlib.sha256).digest()
        return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


@lru_cache
def get_conversation_token_manager() -> ConversationTokenManager:
    settings = get_settings()
    secret: str | bytes = settings.conversation_signing_secret or _DEVELOPMENT_SECRET
    return ConversationTokenManager(secret, ttl_seconds=settings.conversation_token_ttl_seconds)
