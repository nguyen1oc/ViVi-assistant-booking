from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Shared root defaults load first; backend-local values are more specific
        # and must win (notably the SQLite URL supported by this MVP).
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "AI20K Agent"
    app_env: Literal["development", "production", "test"] = "development"
    app_port: int = Field(default=8000, ge=1, le=65535)
    app_host: str = "0.0.0.0"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    cors_origins: str = "http://localhost:3000,http://localhost:3100"

    # LLM
    openai_api_key: str = ""
    openrouter_api_key: str = ""
    model_name: str = "gpt-5.6-luna"
    classifier_model_name: str = "gpt-4o-mini"
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    llm_reasoning_effort: Literal["none", "low", "medium", "high", "xhigh", "max"] = "low"

    # Use only the current LANGSMITH_* names. Keeping LANGCHAIN_* aliases here
    # would make it ambiguous which local configuration is active.
    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "vinfast-test-drive"
    langsmith_event_logs: bool = False
    langsmith_endpoint: str = Field(default="", validation_alias="LANGSMITH_ENDPOINT")
    langsmith_workspace_id: str = Field(default="", validation_alias="LANGSMITH_WORKSPACE_ID")

    # Database
    database_url: str = "postgresql://vinfast:vinfast@localhost:5432/vinfast_booking"
    auto_load_eval_data: bool = True
    eval_data_dir: str = "eval/data"
    booking_advance_window_days: int = Field(default=30, ge=1, le=365)
    redis_enabled: bool = True
    redis_url: str = "redis://localhost:6379/0"

    # Media: local development serves MEDIA_ROOT at /media. Production can set
    # MEDIA_BASE_URL to an absolute CDN origin without changing API DTOs.
    media_root: str = "./data/media"
    media_base_url: str = "/media"

    # Địa chỉ trang công khai, dùng để đặt link trong email gửi cho khách. Email
    # không hiểu đường dẫn tương đối nên chỗ này bắt buộc phải là URL tuyệt đối.
    public_site_url: str = "http://localhost:3000"

    # Vector Store
    chroma_persist_dir: str = "./data/chroma"

    # Zalo Bot: polling is suitable for local demos; production should use a webhook.
    zalo_bot_token: str = ""
    zalo_bot_api_base_url: str = "https://bot-api.zaloplatforms.com"
    zalo_bot_enabled: bool = False
    zalo_bot_polling_enabled: bool = False
    zalo_bot_poll_timeout_seconds: int = Field(default=25, ge=1, le=50)
    zalo_bot_processed_message_retention_days: int = Field(default=30, ge=1, le=365)
    booking_access_otp_ttl_seconds: int = Field(default=60, ge=60, le=900)
    booking_access_otp_resend_cooldown_seconds: int = Field(default=60, ge=1, le=900)
    booking_access_otp_max_attempts: int = Field(default=2, ge=1, le=10)
    # A server-only pepper used in addition to each OTP's per-record salt.
    booking_access_otp_secret: str = ""
    # Local-only escape hatch for deterministic UI testing. Production ignores it.
    booking_access_expose_mock_otp: bool = False
    # Floating Demo Bar is an opt-in simulation, also supported in production.
    # Its API only searches availability; real bookings still require OTP.
    floating_demo_enabled: bool = False

    # Internal portal sessions are opaque, revocable bearer tokens stored as
    # hashes in the database. Staff/manager/admin accounts are provisioned via
    # scripts/manage_internal_user.py; no default credential is created.
    internal_session_ttl_seconds: int = Field(default=28_800, ge=900, le=86_400)

    # Gmail notification provider. Gmail is opt-in so local development keeps
    # the deterministic in-memory sender unless the operator enables it.
    gmail_enabled: bool = False
    gmail_client_id: str = ""
    gmail_client_secret: str = ""
    gmail_refresh_token: str = ""
    gmail_sender_email: str = ""
    gmail_sender_name: str = "VinFast"
    gmail_timeout_seconds: int = Field(default=15, ge=1, le=60)
    notification_poll_interval_seconds: int = Field(default=60, ge=5, le=300)
    notification_batch_size: int = Field(default=100, ge=1, le=500)
    notification_processing_timeout_seconds: int = Field(default=300, ge=30, le=3600)
    driver_chat_base_url: str = "http://localhost:3000/booking#driver-invitation="
    driver_chat_invitation_ttl_seconds: int = Field(default=604_800, ge=900, le=2_592_000)

    # Deterministic AI guardrails. These checks run before the agent, before
    # tool execution, and before a chat response crosses the public API.
    guardrails_enabled: bool = True
    guardrails_max_payload_bytes: int = Field(default=16_384, ge=1_024, le=1_048_576)
    guardrails_max_payload_depth: int = Field(default=6, ge=1, le=20)
    guardrails_max_payload_nodes: int = Field(default=256, ge=16, le=10_000)
    guardrails_max_payload_string_chars: int = Field(default=5_000, ge=128, le=100_000)
    guardrails_max_tool_calls_per_message: int = Field(default=3, ge=1, le=8)
    guardrails_max_output_chars: int = Field(default=8_000, ge=256, le=100_000)
    guardrails_abuse_max_strikes: int = Field(default=3, ge=1, le=10)
    guardrails_abuse_strike_window_seconds: int = Field(default=3_600, ge=60, le=604_800)
    guardrails_abuse_ban_seconds: int = Field(default=86_400, ge=60, le=2_592_000)

    # Public conversation IDs are signed bearer capabilities.  A dedicated
    # secret prevents a client-selected LangGraph thread ID from joining
    # another browser's persisted conversation.
    conversation_signing_secret: str = ""
    conversation_token_ttl_seconds: int = Field(default=28_800, ge=300, le=604_800)

    # Public endpoint rate limits. Anonymous users are identified by a
    # server-issued cookie plus an IP fallback.
    rate_limit_enabled: bool = True
    rate_limit_trust_proxy_headers: bool = False
    rate_limit_anon_cookie_name: str = "anon_session_id"
    rate_limit_anon_cookie_ttl_seconds: int = Field(default=2_592_000, ge=60, le=31_536_000)
    rate_limit_chat_per_session_per_minute: int = Field(default=30, ge=1, le=10_000)
    rate_limit_chat_per_session_per_hour: int = Field(default=120, ge=1, le=100_000)
    rate_limit_chat_per_ip_per_minute: int = Field(default=60, ge=1, le=100_000)
    rate_limit_chat_per_ip_per_hour: int = Field(default=600, ge=1, le=1_000_000)
    rate_limit_demo_action_per_session_per_minute: int = Field(default=30, ge=1, le=10_000)
    rate_limit_demo_action_per_session_per_hour: int = Field(default=300, ge=1, le=100_000)
    rate_limit_demo_action_per_ip_per_minute: int = Field(default=120, ge=1, le=100_000)
    rate_limit_demo_action_per_ip_per_hour: int = Field(default=1_200, ge=1, le=1_000_000)
    # Thiệp mời là endpoint công khai, không đăng nhập, và mã lịch chỉ có 6 ký tự hex
    # nên phải chặn dò mã. Quota để rộng cho khách thật mở lại thiệp nhiều lần.
    rate_limit_invitation_per_ip_per_minute: int = Field(default=20, ge=1, le=10_000)
    rate_limit_invitation_per_ip_per_hour: int = Field(default=120, ge=1, le=100_000)
    rate_limit_otp_request_per_contact_per_hour: int = Field(default=10, ge=1, le=1_000)
    rate_limit_otp_verify_per_challenge_per_minute: int = Field(default=5, ge=1, le=1_000)

    # LLM money budget. The app estimates cost before calling the provider and
    # records actual usage when provider metadata is available.
    llm_daily_budget_enabled: bool = True
    llm_daily_max_cost_usd: float = Field(default=20.0, ge=0.0)
    llm_session_max_cost_usd_per_day: float = Field(default=1.0, ge=0.0)
    llm_max_calls_per_turn: int = Field(default=16, ge=1, le=32)
    llm_estimated_input_token_price_per_1m: float = Field(default=0.15, ge=0.0)
    llm_estimated_output_token_price_per_1m: float = Field(default=0.60, ge=0.0)
    llm_estimated_output_tokens_per_call: int = Field(default=700, ge=1, le=100_000)
    llm_request_timeout_seconds: float = Field(default=60.0, ge=5.0, le=300.0)
    llm_max_retries: int = Field(default=1, ge=0, le=5)

    @model_validator(mode="after")
    def require_production_otp_secret(self):
        if self.app_env == "production" and len(self.booking_access_otp_secret) < 32:
            raise ValueError("BOOKING_ACCESS_OTP_SECRET must be at least 32 characters in production.")
        if self.app_env == "production" and not self.guardrails_enabled:
            raise ValueError("GUARDRAILS_ENABLED cannot be false in production.")
        if self.app_env == "production" and len(self.conversation_signing_secret) < 32:
            raise ValueError("CONVERSATION_SIGNING_SECRET must be at least 32 characters in production.")
        if self.app_env == "production" and not self.rate_limit_enabled:
            raise ValueError("RATE_LIMIT_ENABLED cannot be false in production.")
        if self.gmail_enabled:
            missing = [
                name
                for name, value in (
                    ("GMAIL_CLIENT_ID", self.gmail_client_id),
                    ("GMAIL_CLIENT_SECRET", self.gmail_client_secret),
                    ("GMAIL_REFRESH_TOKEN", self.gmail_refresh_token),
                    ("GMAIL_SENDER_EMAIL", self.gmail_sender_email),
                )
                if not value
            ]
            if missing:
                raise ValueError(f"Missing Gmail settings: {', '.join(missing)}")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
