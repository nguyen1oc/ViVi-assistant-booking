from __future__ import annotations

import base64
from collections.abc import Sequence
from email.message import EmailMessage
from email.utils import formataddr
from typing import cast

import requests  # type: ignore[import-untyped]

from src.services.booking.email_templates import InlineImage, render_otp_email
from src.services.booking.notifications import ProviderResult

TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


class GmailMessagingProvider:
    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        sender_email: str,
        sender_name: str = "VinFast",
        timeout_seconds: int = 15,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.sender_email = sender_email
        self.sender_name = sender_name
        self.timeout_seconds = timeout_seconds

    def send(self, *, channel: str, destination: str, code: str, expires_in_seconds: int) -> ProviderResult:
        rendered = render_otp_email(code=code, expires_in_seconds=expires_in_seconds)
        return self.send_message(
            channel=channel,
            destination=destination,
            subject=rendered.subject,
            body=rendered.plain_text,
            html_body=rendered.html,
            inline_images=rendered.inline_images,
        )

    def send_message(
        self,
        *,
        channel: str,
        destination: str,
        body: str,
        subject: str | None = None,
        html_body: str | None = None,
        inline_images: Sequence[InlineImage] = (),
    ) -> ProviderResult:
        if channel != "email":
            raise ValueError("GmailMessagingProvider only supports the email channel")
        try:
            access_token = self._access_token()
            message = self._mime_message(
                destination=destination,
                subject=subject or "VinFast",
                body=body,
                html_body=html_body,
                inline_images=inline_images,
            )
            response = requests.post(
                GMAIL_SEND_URL,
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                json={"raw": base64.urlsafe_b64encode(message.as_bytes()).decode().rstrip("=")},
                timeout=self.timeout_seconds,
            )
        except requests.Timeout:
            return self._failure("timeout", retryable=True)
        except requests.HTTPError as error:
            status_code = error.response.status_code if error.response is not None else None
            retryable = status_code in {408, 429, 500, 502, 503, 504}
            return self._failure(f"oauth_error_{status_code or 'unknown'}", retryable=retryable)
        except requests.RequestException as error:
            return self._failure(type(error).__name__, retryable=True)

        if response.ok:
            payload = response.json()
            return ProviderResult(
                provider="gmail",
                channel="email",
                provider_status="sent",
                provider_message_id=payload.get("id"),
                is_mock=False,
                retryable=False,
                sanitized_response={"id": payload.get("id"), "threadId": payload.get("threadId")},
            )

        retryable = response.status_code in {408, 429, 500, 502, 503, 504}
        error_code = self._error_code(response)
        return ProviderResult(
            provider="gmail",
            channel="email",
            provider_status=f"error_{response.status_code}",
            provider_message_id=None,
            is_mock=False,
            retryable=retryable,
            sanitized_response={"status_code": response.status_code, "error": error_code},
        )

    def _access_token(self) -> str:
        response = requests.post(
            TOKEN_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise requests.RequestException("missing_access_token")
        return token

    def _mime_message(
        self,
        *,
        destination: str,
        subject: str,
        body: str,
        html_body: str | None,
        inline_images: Sequence[InlineImage] = (),
    ) -> EmailMessage:
        message = EmailMessage()
        message["To"] = destination
        message["From"] = formataddr((self.sender_name, self.sender_email))
        message["Subject"] = subject
        message.set_content(body)
        if html_body:
            message.add_alternative(html_body, subtype="html")
            # Logo đầu thư đi kèm dưới dạng ảnh inline (multipart/related) chứ không phải
            # `data:` URI — Gmail chặn ảnh data:. `add_related` phải gọi TRÊN phần HTML, không
            # phải trên message gốc, nếu không thư thành đính kèm rời và ảnh không hiện.
            # `cast` vì stub của thư viện khai báo get_payload()/iter_parts() trả Message
            # chung chung, không lộ add_related; phần vừa thêm chắc chắn là EmailMessage.
            html_part = cast(EmailMessage, list(message.iter_parts())[-1])
            for image in inline_images:
                html_part.add_related(
                    image.content,
                    maintype="image",
                    subtype=image.subtype,
                    cid=f"<{image.cid}>",
                )
        return message

    @staticmethod
    def _error_code(response: requests.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return response.reason or "http_error"
        error = payload.get("error") or {}
        if isinstance(error, dict):
            return str(error.get("status") or error.get("message") or "gmail_error")
        return str(error)

    @staticmethod
    def _failure(error_code: str, *, retryable: bool) -> ProviderResult:
        return ProviderResult(
            provider="gmail",
            channel="email",
            provider_status="error",
            provider_message_id=None,
            is_mock=False,
            retryable=retryable,
            sanitized_response={"error": error_code},
        )
