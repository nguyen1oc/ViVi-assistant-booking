from __future__ import annotations

import base64
import hashlib
import hmac
import re
from dataclasses import asdict, dataclass

from src.config import get_settings
from src.database import Database

_TOKEN_VERSION = "v1"
_TOKEN_CONTEXT = b"vinfast-public-booking-invitation:v1:"
_DEVELOPMENT_SECRET = "development-public-invitation-secret"
_TOKEN_RE = re.compile(r"^v1\.([A-Za-z0-9_-]{4,128})\.([A-Za-z0-9_-]{32,64})$")


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class PublicInvitationTokenManager:
    """Create deterministic, tamper-evident links for a public booking code.

    A booking code follows the active appointment when it is rescheduled. Signing
    that code, instead of an internal booking row id, keeps the invitation URL
    stable while the resolved time and showroom always come from the latest row.
    """

    def __init__(self, secret: str | bytes) -> None:
        self._secret = secret.encode("utf-8") if isinstance(secret, str) else secret
        if not self._secret:
            raise ValueError("public invitation signing secret cannot be empty")

    def issue(self, booking_code: str) -> str:
        code = str(booking_code or "").strip()
        if not code:
            raise ValueError("booking code is required")
        payload = _b64encode(code.encode("utf-8"))
        return f"{_TOKEN_VERSION}.{payload}.{self._signature(payload)}"

    def verify(self, token: str) -> str | None:
        match = _TOKEN_RE.fullmatch(str(token or ""))
        if not match:
            return None
        payload, signature = match.groups()
        if not hmac.compare_digest(signature, self._signature(payload)):
            return None
        try:
            booking_code = _b64decode(payload).decode("utf-8")
        except (UnicodeDecodeError, ValueError):
            return None
        booking_code = booking_code.strip()
        return booking_code if booking_code else None

    def _signature(self, payload: str) -> str:
        digest = hmac.new(
            self._secret,
            _TOKEN_CONTEXT + payload.encode("ascii"),
            hashlib.sha256,
        ).digest()
        return _b64encode(digest)


def get_public_invitation_token_manager() -> PublicInvitationTokenManager:
    # Production already requires BOOKING_ACCESS_OTP_SECRET to contain at least
    # 32 characters. A domain-separated HMAC safely reuses it without adding a
    # deployment variable that could make outgoing email links fail at runtime.
    secret = get_settings().booking_access_otp_secret or _DEVELOPMENT_SECRET
    return PublicInvitationTokenManager(secret)


def public_invitation_url(booking_code: str) -> str:
    site = get_settings().public_site_url.rstrip("/")
    token = get_public_invitation_token_manager().issue(booking_code)
    return f"{site}/invitation/{token}"


def _vehicle_id(model_code: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", str(model_code or "").casefold()).strip("-")
    aliases = {
        "vfmpv7": "vf-mpv-7",
        "vf-mpv7": "vf-mpv-7",
        "ecvan": "ec-van",
    }
    return aliases.get(normalized, normalized)


@dataclass(frozen=True, slots=True)
class PublicInvitation:
    guest_name: str
    start_at: str
    vehicle_id: str
    model: str
    showroom: str
    address: str
    booking_code: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


class PublicInvitationService:
    def __init__(
        self,
        database: Database,
        token_manager: PublicInvitationTokenManager | None = None,
    ) -> None:
        self.db = database
        self.token_manager = token_manager or get_public_invitation_token_manager()

    def resolve(self, token: str) -> PublicInvitation:
        booking_code = self.token_manager.verify(token)
        if not booking_code:
            raise KeyError("INVITATION_INVALID")

        with self.db.connect() as connection:
            row = connection.execute(
                "SELECT b.booking_code,b.status,driver.full_name guest_name,"
                "t.start_at,m.code model_code,m.name model_name,v.name variant_name,"
                "s.name showroom_name,s.address showroom_address "
                "FROM bookings b "
                "JOIN people driver ON driver.id=b.driver_person_id "
                "JOIN test_drive_slots t ON t.id=b.slot_id "
                "JOIN demo_vehicles d ON d.id=t.demo_vehicle_id "
                "JOIN vehicle_variants v ON v.id=d.variant_id "
                "JOIN vehicle_models m ON m.id=v.model_id "
                "JOIN showrooms s ON s.id=t.showroom_id "
                "WHERE b.booking_code=? "
                "AND b.status IN ('confirmed','checked_in','completed','no_show')",
                (booking_code,),
            ).fetchone()
        if not row:
            raise KeyError("INVITATION_UNAVAILABLE")

        base_model = str(row["model_name"] or row["model_code"] or "VinFast").strip()
        if not base_model.casefold().startswith("vinfast"):
            base_model = f"VinFast {base_model}"
        variant = str(row["variant_name"] or "").strip()
        model = f"{base_model} {variant}".strip() if variant.casefold() not in base_model.casefold() else base_model
        return PublicInvitation(
            guest_name=str(row["guest_name"] or "Khách hàng VinFast"),
            start_at=str(row["start_at"]),
            vehicle_id=_vehicle_id(str(row["model_code"] or "")),
            model=model,
            showroom=str(row["showroom_name"] or "Showroom VinFast"),
            address=str(row["showroom_address"] or ""),
            booking_code=str(row["booking_code"]),
        )
