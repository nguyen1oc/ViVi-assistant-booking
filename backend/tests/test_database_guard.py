import pytest
from src.database.guard import DatabaseSchemaError, QueryGuard


def test_query_guard_ignores_extract_from_qualified_column():
    guard = QueryGuard()

    guard.validate(
        "SELECT EXTRACT(HOUR FROM s.start_at::timestamptz) "
        "FROM test_drive_slots s JOIN demo_vehicles d ON d.id=s.demo_vehicle_id"
    )


def test_query_guard_still_rejects_unknown_tables():
    guard = QueryGuard()

    with pytest.raises(DatabaseSchemaError, match="Unknown table"):
        guard.validate("SELECT * FROM unknown_records")
