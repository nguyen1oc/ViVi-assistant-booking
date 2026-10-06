from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any, Protocol
from uuid import uuid4

from src.services.booking.email_templates import render_otp_email


@dataclass(frozen=True)
class ProviderResult:
    provider: str
    channel: str
    provider_status: str
    provider_message_id: str | None
    is_mock: bool
    retryable: bool = False
    sanitized_response: dict | None = None


class MessagingProvider(Protocol):
    def send_message(
        self,
        *,
        channel: str,
        destination: str,
        body: str,
        subject: str | None = None,
        html_body: str | None = None,
        # Ảnh nhúng trong thân HTML (logo đầu thư). Adapter nào không hỗ trợ thì bỏ qua —
        # thư vẫn đọc được, chỉ mất logo.
        inline_images: Sequence[Any] = (),
    ) -> ProviderResult: ...


class OtpSender(Protocol):
    def send(self, *, channel: str, destination: str, code: str, expires_in_seconds: int) -> ProviderResult: ...


@dataclass
class SentOtp:
    channel: str
    destination: str
    code: str
    expires_in_seconds: int


class InMemoryMessagingProvider:
    """Deterministic development adapter with an explicit mock contract."""

    def __init__(self) -> None:
        self.messages: list[dict] = []

    def send_message(
        self,
        *,
        channel: str,
        destination: str,
        body: str,
        subject: str | None = None,
        html_body: str | None = None,
        inline_images: Sequence[Any] = (),
    ) -> ProviderResult:
        message_id = f"mock_{uuid4().hex}"
        self.messages.append(
            {
                "channel": channel,
                "destination": destination,
                "subject": subject,
                "body": body,
                "html_body": html_body,
                # Ghi lại để test bắt được trường hợp thân thư trỏ vào cid:... mà
                # không có ảnh nào đi kèm — lỗi này chỉ lộ ra khi mở thư thật.
                "inline_images": list(inline_images),
                "id": message_id,
            }
        )
        return ProviderResult(
            provider=f"mock_{channel}",
            channel=channel,
            provider_status="mocked",
            provider_message_id=message_id,
            is_mock=True,
            sanitized_response={"accepted": True},
        )


class InMemoryOtpSender(InMemoryMessagingProvider):
    def __init__(self) -> None:
        super().__init__()
        self.sent: list[SentOtp] = []

    def send(self, *, channel: str, destination: str, code: str, expires_in_seconds: int) -> ProviderResult:
        self.sent.append(SentOtp(channel, destination, code, expires_in_seconds))
        rendered = render_otp_email(code=code, expires_in_seconds=expires_in_seconds)
        return self.send_message(
            channel=channel,
            destination=destination,
            subject=rendered.subject,
            body=rendered.plain_text,
            html_body=rendered.html,
        )
        return self.send_message(
            channel=channel,
            destination=destination,
            body=f"OTP có hiệu lực trong {expires_in_seconds} giây: {code}",
        )


class RoutingMessagingProvider:
    """Sends Zalo through its real adapter and keeps unsupported channels as mocks."""

    def __init__(self, *, zalo_provider: MessagingProvider | None, fallback: MessagingProvider | None = None) -> None:
        self.zalo_provider = zalo_provider
        self.fallback = fallback or InMemoryMessagingProvider()

    def send_message(
        self,
        *,
        channel: str,
        destination: str,
        body: str,
        subject: str | None = None,
        html_body: str | None = None,
        inline_images: Sequence[Any] = (),
    ) -> ProviderResult:
        if channel == "zalo" and self.zalo_provider:
            return self.zalo_provider.send_message(
                channel=channel,
                destination=destination,
                body=body,
            )
        return self.fallback.send_message(
            channel=channel,
            destination=destination,
            body=body,
            subject=subject,
            html_body=html_body,
            inline_images=inline_images,
        )


def provider_result_dict(result: ProviderResult) -> dict:
    return asdict(result)
