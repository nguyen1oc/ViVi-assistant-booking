from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from src.database import Database
from src.services.booking.notifications import MessagingProvider, provider_result_dict


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    return value.isoformat()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class DriverInvitation:
    booking_id: str
    driver_person_id: str
    driver_name: str
    email: str
    phone: str
    expires_at: str


@dataclass(frozen=True)
class DriverInvitationLink:
    booking_id: str
    driver_name: str
    email: str
    url: str
    expires_at: str


class DriverInvitationService:
    def __init__(
        self,
        database: Database,
        messaging_provider: MessagingProvider,
        *,
        base_url: str,
        ttl_seconds: int,
    ) -> None:
        self.db = database
        self.messaging_provider = messaging_provider
        self.base_url = base_url.rstrip("/")
        self.ttl_seconds = ttl_seconds

    def issue_and_send(self, booking_id: str) -> dict:
        invite = self.issue(booking_id)
        result = self.messaging_provider.send_message(
            channel="email",
            destination=invite.email,
            subject="Mời bạn chuẩn bị cho buổi lái thử VinFast",
            body=(
                f"Xin chào {invite.driver_name},\n\n"
                "Bạn được mời trò chuyện riêng với ViVi để chia sẻ nhu cầu và chuẩn bị cho buổi lái thử. "
                f"Bạn có thể mở liên kết sau: {invite.url}\n\n"
                f"Liên kết hết hạn lúc {invite.expires_at}."
            ),
        )
        return {
            "booking_id": booking_id,
            "status": "sent",
            "expires_at": invite.expires_at,
            "delivery": provider_result_dict(result),
        }

    def issue(self, booking_id: str) -> DriverInvitationLink:
        now = _now()
        token = secrets.token_urlsafe(32)
        expires_at = now + timedelta(seconds=self.ttl_seconds)
        invitation_id = f"driver_invite_{uuid.uuid4().hex}"
        with self.db.transaction(immediate=True) as c:
            booking = c.execute(
                "SELECT b.booker_person_id,b.driver_person_id,p.full_name,p.email,p.normalized_email "
                "FROM bookings b JOIN people p ON p.id=b.driver_person_id WHERE b.id=?",
                (booking_id,),
            ).fetchone()
            if not booking:
                raise KeyError(booking_id)
            if booking["driver_person_id"] == booking["booker_person_id"]:
                raise ValueError("DRIVER_IS_BOOKER")
            email = str(booking["normalized_email"] or booking["email"] or "").strip().casefold()
            if not email:
                raise ValueError("DRIVER_EMAIL_REQUIRED")
            c.execute(
                "UPDATE driver_chat_invitations SET status='revoked',revoked_at=?,updated_at=? "
                "WHERE booking_id=? AND status='active'",
                (_iso(now), _iso(now), booking_id),
            )
            c.execute(
                "INSERT INTO driver_chat_invitations "
                "(id,booking_id,driver_person_id,token_hash,status,expires_at,created_at,updated_at) "
                "VALUES(?,?,?,?,'active',?,?,?)",
                (invitation_id, booking_id, booking["driver_person_id"], _token_hash(token), _iso(expires_at), _iso(now), _iso(now)),
            )

        link = (
            f"{self.base_url}{token}"
            if self.base_url.endswith("driver-invitation=")
            else f"{self.base_url}/{token}"
        )
        with self.db.transaction(immediate=True) as c:
            c.execute(
                "UPDATE driver_chat_invitations SET sent_at=?,updated_at=? WHERE id=?",
                (_iso(now), _iso(now), invitation_id),
            )
        return DriverInvitationLink(
            booking_id=booking_id,
            driver_name=str(booking["full_name"] or ""),
            email=email,
            url=link,
            expires_at=_iso(expires_at),
        )

    def resolve(self, token: str) -> DriverInvitation:
        now = _now()
        with self.db.transaction(immediate=True) as c:
            row = c.execute(
                "SELECT i.booking_id,i.driver_person_id,i.expires_at,p.full_name,p.email,p.normalized_email,p.phone,p.normalized_phone "
                "FROM driver_chat_invitations i JOIN people p ON p.id=i.driver_person_id "
                "JOIN bookings b ON b.id=i.booking_id AND b.driver_person_id=i.driver_person_id "
                "AND b.status IN ('confirmed','checked_in') "
                "WHERE i.token_hash=? AND i.status='active'",
                (_token_hash(token),),
            ).fetchone()
            if not row:
                raise KeyError("INVITATION_INVALID")
            expires_at = datetime.fromisoformat(str(row["expires_at"]))
            if expires_at <= now:
                c.execute(
                    "UPDATE driver_chat_invitations SET status='expired',updated_at=? WHERE token_hash=?",
                    (_iso(now), _token_hash(token)),
                )
                raise KeyError("INVITATION_EXPIRED")
            email = str(row["normalized_email"] or row["email"] or "").strip().casefold()
            if not email:
                raise KeyError("INVITATION_IDENTITY_UNAVAILABLE")
        return DriverInvitation(
            booking_id=str(row["booking_id"]),
            driver_person_id=str(row["driver_person_id"]),
            driver_name=str(row["full_name"] or ""),
            email=email,
            phone=str(row["normalized_phone"] or row["phone"] or ""),
            expires_at=str(row["expires_at"]),
        )
