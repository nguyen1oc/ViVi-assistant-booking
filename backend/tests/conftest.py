import os
from datetime import UTC, datetime, timedelta

# Override DATABASE_URL to use SQLite for tests before importing the app
os.environ["DATABASE_URL"] = "sqlite:///./data/test.db"

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from src.database import Database
from src.dependencies import database as app_database
from src.main import app
from src.services.booking import BookingService

FIXED_NOW = datetime(2026, 8, 3, 2, 0, tzinfo=UTC)
BOOKER_PHONE = "0901234567"

# ASGITransport does not run FastAPI's lifespan by default.  Initialise the
# same global SQLite database used by the imported app so middleware and LLM
# budget services see the current schema during API and node tests.
app_database.initialize()


@pytest_asyncio.fixture
async def client():
    """Async HTTP client for testing API endpoints."""
    from src.guardrails.abuse import get_abuse_tracker

    abuse_tracker = get_abuse_tracker()
    abuse_tracker.clear()
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        abuse_tracker.clear()


@pytest.fixture(autouse=True)
def mock_llm():
    """Mock ChatOpenAI globally to avoid real API calls and import order issues."""
    from langchain_core.messages import AIMessage

    mock_instance = MagicMock()
    mock_instance.model_name = "test-chat-model"
    mock_response = AIMessage(content="Mocked LLM response")

    # Mock basic invoke/ainvoke
    mock_instance.ainvoke = AsyncMock(return_value=mock_response)

    # Mock bind_tools to return the mock instance so we can chain ainvoke on it
    mock_instance.bind_tools = MagicMock(return_value=mock_instance)

    # Mock with_structured_output for classifier_node
    mock_structured = MagicMock()
    from src.agents.nodes.classifier_node import RouteSchema

    async def mock_classify(prompt, **kwargs):
        prompt_lower = prompt.lower()
        query_part = prompt_lower.split("user query:")[-1] if "user query:" in prompt_lower else prompt_lower
        # Remove punctuation to ensure clean word splitting
        query_clean = "".join(c if c.isalnum() or c.isspace() else " " for c in query_part)
        words = query_clean.split()
        if any(phrase in query_part for phrase in ["bạn là ai", "vivi là ai", "hỗ trợ gì", "làm được gì"]):
            return RouteSchema(intent="domain", sub_intent="assistant_identity", has_schedule_preference=False)
        if any(kw in words for kw in ["chào", "hello", "hi", "alo"]):
            return RouteSchema(intent="domain", sub_intent="greeting", has_schedule_preference=False)
        elif any(kw in words or kw in query_part for kw in ["vf8", "sạc", "km", "thông số", "giá"]):
            return RouteSchema(intent="domain", sub_intent="vehicle_info", has_schedule_preference=False)
        return RouteSchema(intent="domain", sub_intent="booking", has_schedule_preference=False)

    mock_structured.ainvoke = AsyncMock(side_effect=mock_classify)
    mock_instance.with_structured_output = MagicMock(return_value=mock_structured)

    # Patch the node-level dependencies as well as the provider constructor.
    # get_llm()/get_classifier_llm() intentionally return None when no API key
    # is configured, which is the normal state inside the test container.
    with (
        patch("src.services.llm.ChatOpenAI", return_value=mock_instance),
        patch("src.agents.nodes.classifier_node.get_classifier_llm", return_value=mock_instance),
        patch("src.agents.nodes.booking_skill_node.get_llm", return_value=mock_instance),
        patch("src.agents.nodes.post_booking_skill_node.get_llm", return_value=mock_instance),
    ):
        yield mock_instance


@pytest.fixture
def booking_db(tmp_path):
    """Create a fresh isolated SQLite database for every service testcase."""
    database = Database(tmp_path / "booking-test.db")
    database.initialize()
    return database


@pytest.fixture
def booking_service(booking_db):
    return BookingService(booking_db, otp_secret="test-secret", now=lambda: FIXED_NOW)


@pytest.fixture
def catalog(booking_db):
    """Seed a minimal catalog containing ready, low-battery and unavailable vehicles."""
    created = FIXED_NOW.isoformat()
    primary_start = FIXED_NOW + timedelta(days=2, hours=8)
    with booking_db.transaction(immediate=True) as connection:
        connection.executemany(
            """INSERT INTO vehicle_models(
                id,code,name,vehicle_type,required_license_class,
                license_requirement_note,is_active,created_at,updated_at,seat_count
            ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            [
                # Cot cuoi la seat_count. Thu xac nhan doc cot nay de noi "xe may cho";
                # de trong thi menh de do bi bo im lang.
                ("model_vf6", "VF6", "VinFast VF 6", "SUV", "B1", "GPLX B1", 1, created, created, 5),
                ("model_inactive", "VFX", "VinFast Inactive", "SUV", "B1", "GPLX B1", 0, created, created, 5),
            ],
        )
        connection.execute(
            """INSERT INTO vehicle_variants(
                id,model_id,code,name,battery_capacity_kwh,estimated_range_km,
                motor_power_kw,is_active,created_at,updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            ("variant_plus", "model_vf6", "VF6-PLUS", "Plus", 59.6, 399, 150, 1, created, created),
        )
        connection.executemany(
            """INSERT INTO showrooms(
                id,code,name,address,latitude,longitude,phone,email,timezone,
                is_active,created_at,updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            [
                (
                    "showroom_q7",
                    "Q7",
                    "VinFast Quận 7",
                    "Quận 7",
                    10.729,
                    106.721,
                    None,
                    None,
                    "Asia/Ho_Chi_Minh",
                    1,
                    created,
                    created,
                ),
                (
                    "showroom_gv",
                    "GV",
                    "VinFast Gò Vấp",
                    "Gò Vấp",
                    10.838,
                    106.665,
                    None,
                    None,
                    "Asia/Ho_Chi_Minh",
                    1,
                    created,
                    created,
                ),
                (
                    "showroom_inactive",
                    "OFF",
                    "Showroom đóng cửa",
                    "TP.HCM",
                    10.8,
                    106.7,
                    None,
                    None,
                    "Asia/Ho_Chi_Minh",
                    0,
                    created,
                    created,
                ),
            ],
        )
        connection.executemany(
            """INSERT INTO demo_vehicles(
                id,showroom_id,variant_id,asset_code,vin,plate_number,
                operational_status,battery_soc,minimum_booking_soc,charging_status,
                is_active,created_at,updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [
                (
                    "demo_main",
                    "showroom_q7",
                    "variant_plus",
                    "DEMO-01",
                    None,
                    None,
                    "available",
                    80,
                    20,
                    "not_charging",
                    1,
                    created,
                    created,
                ),
                (
                    "demo_second",
                    "showroom_q7",
                    "variant_plus",
                    "DEMO-02",
                    None,
                    None,
                    "available",
                    75,
                    20,
                    "not_charging",
                    1,
                    created,
                    created,
                ),
                (
                    "demo_gv",
                    "showroom_gv",
                    "variant_plus",
                    "DEMO-03",
                    None,
                    None,
                    "available",
                    70,
                    20,
                    "not_charging",
                    1,
                    created,
                    created,
                ),
                (
                    "demo_low",
                    "showroom_q7",
                    "variant_plus",
                    "DEMO-LOW",
                    None,
                    None,
                    "available",
                    10,
                    20,
                    "not_charging",
                    1,
                    created,
                    created,
                ),
                (
                    "demo_maintenance",
                    "showroom_q7",
                    "variant_plus",
                    "DEMO-MAINT",
                    None,
                    None,
                    "maintenance",
                    80,
                    20,
                    "not_charging",
                    1,
                    created,
                    created,
                ),
            ],
        )

        slots = [
            (
                "slot_main",
                "showroom_q7",
                "demo_main",
                primary_start,
                primary_start + timedelta(minutes=30),
                "available",
            ),
            (
                "slot_overlap",
                "showroom_q7",
                "demo_main",
                primary_start + timedelta(minutes=15),
                primary_start + timedelta(minutes=45),
                "available",
            ),
            (
                "slot_later",
                "showroom_q7",
                "demo_main",
                primary_start + timedelta(hours=2),
                primary_start + timedelta(hours=2, minutes=30),
                "available",
            ),
            (
                "slot_second_vehicle",
                "showroom_q7",
                "demo_second",
                primary_start,
                primary_start + timedelta(minutes=30),
                "available",
            ),
            ("slot_gv", "showroom_gv", "demo_gv", primary_start, primary_start + timedelta(minutes=30), "available"),
            (
                "slot_low_battery",
                "showroom_q7",
                "demo_low",
                primary_start + timedelta(hours=3),
                primary_start + timedelta(hours=3, minutes=30),
                "available",
            ),
            (
                "slot_maintenance",
                "showroom_q7",
                "demo_maintenance",
                primary_start + timedelta(hours=4),
                primary_start + timedelta(hours=4, minutes=30),
                "available",
            ),
            (
                "slot_blocked",
                "showroom_q7",
                "demo_second",
                primary_start + timedelta(hours=5),
                primary_start + timedelta(hours=5, minutes=30),
                "blocked",
            ),
            (
                "slot_past",
                "showroom_q7",
                "demo_second",
                FIXED_NOW - timedelta(hours=2),
                FIXED_NOW - timedelta(hours=1),
                "available",
            ),
        ]
        connection.executemany(
            """INSERT INTO test_drive_slots(
                id,showroom_id,demo_vehicle_id,start_at,end_at,status,
                held_until,current_booking_id,block_reason,created_at,updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            [
                (
                    slot_id,
                    showroom_id,
                    vehicle_id,
                    start.isoformat(),
                    end.isoformat(),
                    status,
                    None,
                    None,
                    "maintenance" if status == "blocked" else None,
                    created,
                    created,
                )
                for slot_id, showroom_id, vehicle_id, start, end, status in slots
            ],
        )

    return {
        "model": "model_vf6",
        "variant": "variant_plus",
        "showroom_q7": "showroom_q7",
        "showroom_gv": "showroom_gv",
        "slot_main": "slot_main",
        "slot_overlap": "slot_overlap",
        "slot_later": "slot_later",
        "slot_second_vehicle": "slot_second_vehicle",
        "slot_gv": "slot_gv",
        "slot_low_battery": "slot_low_battery",
        "slot_maintenance": "slot_maintenance",
        "slot_blocked": "slot_blocked",
        "slot_past": "slot_past",
        "primary_start": primary_start,
    }


@pytest.fixture
def ready_draft_factory(booking_service, catalog):
    counter = 0

    def create(slot_id=None, *, notification_plan_patch=None):
        nonlocal counter
        counter += 1
        held = booking_service.hold_slot(slot_id or catalog["slot_main"], f"hold:ready-{counter}")
        draft = booking_service.update_booking_draft(
            held["booking_id"],
            booker_patch={
                "full_name": "Huynh Thi Hai Chau",
                "phone": BOOKER_PHONE,
                "email": "chau@example.test",
                "preferred_channel": "sms",
            },
            driver_same_as_booker=True,
            license_patch={
                "has_driving_license": True,
                "declared_license_class": "B1",
                "validity_acknowledged": True,
            },
            notification_plan_patch=notification_plan_patch,
            expected_version=1,
        )
        return {"held": held, "draft": draft, "booking_id": held["booking_id"]}

    return create


@pytest.fixture
def confirmed_booking_factory(booking_service, ready_draft_factory):
    counter = 0

    def create(slot_id=None, *, notification_plan_patch=None):
        nonlocal counter
        counter += 1
        prepared = ready_draft_factory(slot_id, notification_plan_patch=notification_plan_patch)
        confirmed = booking_service.confirm_booking(
            prepared["booking_id"],
            f"confirm:{counter}",
            prepared["draft"]["version"],
        )
        return {**prepared, "confirmed": confirmed}

    return create


@pytest.fixture
def access_factory(booking_service, confirmed_booking_factory):
    def create(purpose="lookup", *, confirmed=None):
        booking = confirmed or confirmed_booking_factory()
        challenge = booking_service.request_access(
            booking["confirmed"]["booking_code"],
            BOOKER_PHONE,
            purpose,
            expose_otp=True,
        )
        session = booking_service.verify_access(challenge["challenge_id"], challenge["otp_code"])
        return {"booking": booking, "challenge": challenge, "session": session}

    return create
