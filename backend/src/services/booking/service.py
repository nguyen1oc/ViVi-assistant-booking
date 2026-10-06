from src.database import Database
from src.services.booking.access import AccessService
from src.services.booking.background import BackgroundJobService
from src.services.booking.catalog import CatalogService
from src.services.booking.common import utcnow
from src.services.booking.dashboard import DashboardService
from src.services.booking.importer import ImportService
from src.services.booking.lifecycle import LifecycleService
from src.services.booking.location import HaversineMapProvider, MapProvider
from src.services.booking.management import ManagementService
from src.services.booking.notifications import (
    InMemoryMessagingProvider,
    InMemoryOtpSender,
    MessagingProvider,
    OtpSender,
)
from src.services.booking.staff import StaffOperationService


class BookingService(
    CatalogService,
    LifecycleService,
    AccessService,
    ManagementService,
    StaffOperationService,
    BackgroundJobService,
    ImportService,
    DashboardService,
):
    def __init__(
        self,
        database: Database,
        *,
        otp_secret: str = "development-secret",
        otp_sender: OtpSender | None = None,
        messaging_provider: MessagingProvider | None = None,
        map_provider: MapProvider | None = None,
        otp_max_attempts: int = 5,
        otp_ttl_seconds: int = 300,
        otp_resend_cooldown_seconds: int = 60,
        otp_request_per_contact_per_hour: int = 3,
        otp_verify_per_challenge_per_minute: int = 5,
        access_session_ttl_seconds: int = 1800,
        booking_advance_window_days: int = 30,
        now=utcnow,
    ):
        self.db = database
        self.otp_secret = otp_secret.encode()
        default_sender = otp_sender or InMemoryOtpSender()
        self.otp_sender = default_sender
        self.messaging_provider = messaging_provider or (
            default_sender if hasattr(default_sender, "send_message") else InMemoryMessagingProvider()
        )
        self.map_provider = map_provider or HaversineMapProvider()
        self.otp_max_attempts = otp_max_attempts
        self.otp_ttl_seconds = otp_ttl_seconds
        self.otp_resend_cooldown_seconds = otp_resend_cooldown_seconds
        self.otp_request_per_contact_per_hour = otp_request_per_contact_per_hour
        self.otp_verify_per_challenge_per_minute = otp_verify_per_challenge_per_minute
        self.access_session_ttl_seconds = access_session_ttl_seconds
        self.booking_advance_window_days = booking_advance_window_days
        self.now = now
