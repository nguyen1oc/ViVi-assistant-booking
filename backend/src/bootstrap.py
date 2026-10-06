from __future__ import annotations

import logging
from pathlib import Path

from src.config import Settings
from src.database import Database
from src.services.booking import BookingService

LOGGER = logging.getLogger(__name__)

BOOTSTRAP_TABLES = (
    "vehicle_models",
    "vehicle_variants",
    "showrooms",
    "sales_staff",
    "demo_vehicles",
    "test_drive_slots",
    "people",
    "bookings",
)


def initialize_database(database: Database, settings: Settings) -> dict | None:
    """Create schema and import eval CSVs when the booking dataset is empty."""
    database.initialize()
    if database.raw_url in {":memory:", "sqlite:///:memory:"}:
        LOGGER.info("Eval data auto-load skipped for in-memory database")
        return None
    if not settings.auto_load_eval_data:
        LOGGER.info("Eval data auto-load disabled")
        return None
    if not _booking_dataset_is_empty(database):
        LOGGER.info("Booking dataset already contains rows; eval data auto-load skipped")
        return None

    data_dir = Path(settings.eval_data_dir)
    if not data_dir.is_absolute():
        data_dir = Path.cwd() / data_dir
    if not data_dir.exists():
        LOGGER.warning("Eval data directory not found: %s", data_dir)
        return None

    service = BookingService(database)
    result = service.import_eval_dataset_from_dir(data_dir)
    LOGGER.info("Auto-loaded eval dataset from %s: %s", data_dir, result)
    return result


def _booking_dataset_is_empty(database: Database) -> bool:
    with database.connect() as connection:
        total = sum(connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0] for table in BOOTSTRAP_TABLES)
    return total == 0
