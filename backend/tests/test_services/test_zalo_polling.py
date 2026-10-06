from datetime import UTC, datetime, timedelta

import pytest
from src.services.zalo_bot import ZaloPollingService


class FakeZaloClient:
    def __init__(self):
        self.sent: list[tuple[str, str]] = []
        self.updates: list[list[dict]] = []
        self.requested_offsets: list[int | None] = []

    def send_text(self, chat_id: str, text: str) -> dict:
        self.sent.append((chat_id, text))
        return {"ok": True}

    async def get_updates(self, timeout_seconds: int, offset: int | None = None) -> list[dict]:
        self.requested_offsets.append(offset)
        return self.updates.pop(0) if self.updates else []


def test_zalo_polling_deduplicates_message_ids_in_database(booking_db):
    client = FakeZaloClient()
    first_worker = ZaloPollingService(booking_db, client, timeout_seconds=1)
    second_worker = ZaloPollingService(booking_db, client, timeout_seconds=1)
    update = {"message": {"message_id": "message-1", "text": "LIENKET 0901234567", "chat": {"id": "chat-1"}}}

    first_worker._handle_update(update)
    second_worker._handle_update(update)

    with booking_db.connect() as connection:
        assert connection.execute("SELECT count(*) FROM zalo_identity_links").fetchone()[0] == 1
        assert connection.execute("SELECT count(*) FROM zalo_processed_messages").fetchone()[0] == 1
    assert len(client.sent) == 1


def test_zalo_polling_prunes_only_expired_processed_messages(booking_db):
    service = ZaloPollingService(booking_db, FakeZaloClient(), timeout_seconds=1, retention_days=30)
    now = datetime.now(UTC)
    with booking_db.transaction(immediate=True) as connection:
        connection.execute("INSERT INTO zalo_processed_messages VALUES(?,?)", ("old", (now - timedelta(days=31)).isoformat()))
        connection.execute("INSERT INTO zalo_processed_messages VALUES(?,?)", ("recent", (now - timedelta(days=29)).isoformat()))

    service._cleanup_processed_messages_if_due()

    with booking_db.connect() as connection:
        assert connection.execute("SELECT count(*) FROM zalo_processed_messages WHERE message_id='old'").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM zalo_processed_messages WHERE message_id='recent'").fetchone()[0] == 1


@pytest.mark.asyncio
async def test_zalo_polling_advances_update_offset_after_processing(booking_db):
    client = FakeZaloClient()
    client.updates = [
        [{"update_id": 41, "message": {"message_id": "message-41", "text": "LIENKET 0901234567", "chat": {"id": "chat-1"}}}],
        [],
    ]
    service = ZaloPollingService(booking_db, client, timeout_seconds=1)

    await service.poll_once()
    await service.poll_once()

    assert client.requested_offsets == [None, 42]
