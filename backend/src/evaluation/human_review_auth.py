from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .human_review import default_eval_root
from .human_review_errors import HumanReviewError as InternalPortalError

PASSWORD_ITERATIONS = 310_000
USERNAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,79}$")
_CONFIG_LOCK = threading.Lock()


def _encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _password_digest(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS).hex()


@dataclass(frozen=True)
class HumanReviewer:
    username: str
    display_name: str

    def as_dict(self) -> dict[str, str]:
        return {"id": self.username, "username": self.username, "display_name": self.display_name}


class HumanReviewAuth:
    def __init__(
        self,
        *,
        config_path: Path | None = None,
        session_ttl_seconds: int = 28_800,
        clock: Callable[[], float] = time.time,
    ) -> None:
        eval_root = default_eval_root()
        configured_path = os.getenv("HUMAN_REVIEW_REVIEWERS_PATH", "").strip()
        reviewers_path = Path(configured_path) if configured_path else eval_root / "human" / "reviewers.json"
        if configured_path and not reviewers_path.is_absolute():
            reviewers_path = eval_root / reviewers_path
        self.config_path = config_path or reviewers_path
        self.session_ttl_seconds = session_ttl_seconds
        self.clock = clock

    @staticmethod
    def _empty_config() -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "signing_secret": secrets.token_hex(32),
            "reviewers": {},
        }

    def _config(self, *, required: bool = True) -> dict[str, Any]:
        if not self.config_path.is_file():
            if required:
                raise InternalPortalError(
                    "HUMAN_REVIEW_AUTH_NOT_CONFIGURED",
                    "Human Review Portal chưa có reviewer. Hãy chạy scripts/manage_human_reviewer.py.",
                    status_code=503,
                )
            return self._empty_config()
        try:
            payload = json.loads(self.config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise InternalPortalError(
                "HUMAN_REVIEW_AUTH_INVALID",
                "Không thể đọc cấu hình reviewer.",
                status_code=503,
            ) from exc
        if not isinstance(payload.get("reviewers"), dict) or not payload.get("signing_secret"):
            raise InternalPortalError(
                "HUMAN_REVIEW_AUTH_INVALID",
                "Cấu hình reviewer không hợp lệ.",
                status_code=503,
            )
        return payload

    def _write_config(self, payload: dict[str, Any]) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.config_path.with_suffix(self.config_path.suffix + ".tmp")
        try:
            temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            temporary.replace(self.config_path)
        except OSError as exc:
            raise InternalPortalError(
                "HUMAN_REVIEW_AUTH_NOT_WRITABLE",
                "Không thể lưu tài khoản reviewer; hãy kiểm tra quyền ghi eval/human.",
                status_code=503,
            ) from exc

    def create_reviewer(
        self,
        *,
        username: str,
        display_name: str,
        password: str,
        is_active: bool = True,
    ) -> HumanReviewer:
        normalized = username.strip().casefold()
        if not USERNAME_PATTERN.fullmatch(normalized):
            raise InternalPortalError(
                "INVALID_REVIEWER_USERNAME",
                "Tên reviewer cần 3–80 ký tự: chữ thường, số, dấu chấm, gạch ngang hoặc gạch dưới.",
            )
        if len(password) < 8:
            raise InternalPortalError("WEAK_PASSWORD", "Mật khẩu reviewer phải có ít nhất 8 ký tự.")
        name = display_name.strip()
        if not name or len(name) > 120:
            raise InternalPortalError("INVALID_DISPLAY_NAME", "Tên hiển thị reviewer không hợp lệ.")
        salt = secrets.token_bytes(16)
        with _CONFIG_LOCK:
            config = self._config(required=False)
            existing = config["reviewers"].get(normalized, {})
            config["reviewers"][normalized] = {
                "display_name": name,
                "password_salt": salt.hex(),
                "password_hash": _password_digest(password, salt),
                "is_active": bool(is_active),
                "session_version": int(existing.get("session_version", 0)) + 1,
            }
            self._write_config(config)
        return HumanReviewer(username=normalized, display_name=name)

    def _reviewer_record(self, config: dict[str, Any], username: str) -> dict[str, Any] | None:
        record = config["reviewers"].get(username)
        return record if isinstance(record, dict) else None

    def login(self, username: str, password: str) -> dict[str, Any]:
        normalized = username.strip().casefold()
        config = self._config()
        record = self._reviewer_record(config, normalized)
        if record:
            try:
                expected = _password_digest(password, bytes.fromhex(str(record["password_salt"])))
                valid = bool(record.get("is_active")) and hmac.compare_digest(
                    expected,
                    str(record.get("password_hash") or ""),
                )
            except (KeyError, ValueError):
                valid = False
        else:
            _password_digest(password, b"\0" * 16)
            valid = False
        if not valid or record is None:
            raise InternalPortalError(
                "INVALID_REVIEWER_CREDENTIALS",
                "Tên reviewer hoặc mật khẩu không đúng.",
                status_code=401,
            )
        expires_at = int(self.clock()) + self.session_ttl_seconds
        payload = {
            "sub": normalized,
            "exp": expires_at,
            "ver": int(record.get("session_version", 1)),
        }
        encoded = _encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
        signature = hmac.new(
            bytes.fromhex(str(config["signing_secret"])),
            encoded.encode("ascii"),
            hashlib.sha256,
        ).digest()
        reviewer = HumanReviewer(username=normalized, display_name=str(record["display_name"]))
        return {
            "access_token": f"{encoded}.{_encode(signature)}",
            "token_type": "bearer",
            "expires_at": expires_at,
            "reviewer": reviewer.as_dict(),
        }

    def authenticate(self, token: str) -> HumanReviewer:
        try:
            encoded, supplied_signature = token.split(".", 1)
            config = self._config()
            expected_signature = hmac.new(
                bytes.fromhex(str(config["signing_secret"])),
                encoded.encode("ascii"),
                hashlib.sha256,
            ).digest()
            if not hmac.compare_digest(expected_signature, _decode(supplied_signature)):
                raise ValueError("signature mismatch")
            payload = json.loads(_decode(encoded))
            username = str(payload["sub"])
            record = self._reviewer_record(config, username)
            if (
                not record
                or not record.get("is_active")
                or int(payload["exp"]) <= int(self.clock())
                or int(payload["ver"]) != int(record.get("session_version", 1))
            ):
                raise ValueError("expired or revoked")
        except (InternalPortalError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            if isinstance(exc, InternalPortalError) and exc.code.startswith("HUMAN_REVIEW_AUTH_"):
                raise
            raise InternalPortalError(
                "HUMAN_REVIEW_AUTH_REQUIRED",
                "Phiên Human Review không hợp lệ hoặc đã hết hạn.",
                status_code=401,
            ) from exc
        return HumanReviewer(username=username, display_name=str(record["display_name"]))
