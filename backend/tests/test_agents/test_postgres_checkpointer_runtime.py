import pytest
from src.agents.graph import agent, close_persistent_agent, get_agent, initialize_persistent_agent, uses_postgres


@pytest.mark.parametrize(
    ("database_url", "expected"),
    [
        ("postgresql://user:password@db:5432/app", True),
        ("postgres://user:password@db/app", True),
        ("sqlite:///./data/app.db", False),
    ],
)
def test_detects_postgres_urls(database_url, expected):
    assert uses_postgres(database_url) is expected


@pytest.mark.asyncio
async def test_sqlite_keeps_memory_saver_for_local_tests():
    await initialize_persistent_agent("sqlite:///./data/app.db")
    assert get_agent() is agent
    await close_persistent_agent()
