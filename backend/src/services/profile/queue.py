from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from typing import Any

from pydantic import TypeAdapter

from src.database.redis_client import RedisClient
from src.services.profile.models import BookingSignalCandidate, SignalCandidate
from src.services.profile.service import ProfileService

logger = logging.getLogger("profile.queue")
QUEUE_NAME = "profile-update-v2"
MAX_RETRIES = 3
_CANDIDATES = TypeAdapter(list[SignalCandidate])
_BOOKING_CANDIDATES = TypeAdapter(list[BookingSignalCandidate])


class ProfileUpdateQueue:
    """Reliably persists signals already extracted by the main agent."""

    def __init__(self, redis: RedisClient, profiles: ProfileService) -> None:
        self.redis = redis
        self.profiles = profiles
        self._worker_task: asyncio.Task[None] | None = None

    async def enqueue(self, *, profile_id: str, conversation_id: str, trace_id: str,
                      candidates: list[SignalCandidate]) -> bool:
        if not candidates:
            logger.info("profile.queue.skipped trace_id=%s profile_id=%s reason=no_signals", trace_id, profile_id)
            return True
        if not self.redis.available:
            logger.warning("profile.queue.unavailable trace_id=%s profile_id=%s", trace_id, profile_id)
            return False
        serialized = [candidate.model_dump(mode="json") for candidate in candidates]
        canonical = json.dumps(serialized, ensure_ascii=False, sort_keys=True)
        payload = {"profile_id": profile_id, "conversation_id": conversation_id,
                   "trace_id": trace_id, "candidates": serialized, "retry_count": 0}
        dedupe_key = hashlib.sha256(f"{conversation_id}\0{canonical}".encode()).hexdigest()
        try:
            queued = await asyncio.wait_for(asyncio.to_thread(
                self.redis.enqueue_reliable, QUEUE_NAME, payload, dedupe_key=dedupe_key), timeout=0.5)
        except TimeoutError:
            queued = False
            logger.warning("profile.queue.enqueue_timeout trace_id=%s profile_id=%s", trace_id, profile_id)
        if queued:
            self.start()
            logger.info("profile.queue.enqueued trace_id=%s conversation_id=%s profile_id=%s signal_count=%s",
                        trace_id, conversation_id, profile_id, len(candidates))
        else:
            logger.warning("profile.queue.enqueue_failed trace_id=%s profile_id=%s", trace_id, profile_id)
        return queued

    async def enqueue_post_booking(self, *, profile_updates: list[dict[str, Any]], booking_id: str,
                                   booking_candidates: list[BookingSignalCandidate], speaker_role: str,
                                   conversation_id: str, trace_id: str) -> bool:
        if not profile_updates and not booking_candidates:
            return True
        if not self.redis.available:
            return await self._persist_post_booking_direct(
                profile_updates=profile_updates,
                booking_id=booking_id,
                booking_candidates=booking_candidates,
                speaker_role=speaker_role,
                conversation_id=conversation_id,
                trace_id=trace_id,
                reason="redis_unavailable",
            )
        serialized_booking = [item.model_dump(mode="json") for item in booking_candidates]
        payload = {"profile_updates": profile_updates, "booking_id": booking_id,
                   "booking_candidates": serialized_booking, "speaker_role": speaker_role,
                   "conversation_id": conversation_id, "trace_id": trace_id, "retry_count": 0}
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        dedupe_key = hashlib.sha256(f"{conversation_id}\0{canonical}".encode()).hexdigest()
        try:
            queued = await asyncio.wait_for(asyncio.to_thread(self.redis.enqueue_reliable, QUEUE_NAME, payload, dedupe_key=dedupe_key), timeout=0.5)
        except TimeoutError:
            queued = False
        if queued:
            self.start()
        return queued

    async def _persist_post_booking_direct(
        self,
        *,
        profile_updates: list[dict[str, Any]],
        booking_id: str,
        booking_candidates: list[BookingSignalCandidate],
        speaker_role: str,
        conversation_id: str,
        trace_id: str,
        reason: str,
    ) -> bool:
        """Persist post-booking signals synchronously when Redis is unavailable.

        This path is used only before an enqueue attempt. A timed-out enqueue can
        have reached Redis, so it deliberately remains a failed enqueue rather
        than risking duplicate writes here.
        """
        try:
            for update in profile_updates:
                candidates = _CANDIDATES.validate_python(update.get("candidates") or [])
                if candidates:
                    await asyncio.to_thread(
                        self.profiles.apply,
                        str(update["profile_id"]),
                        candidates,
                        source_ref=conversation_id,
                        trace_id=trace_id,
                    )

            validated_booking = _BOOKING_CANDIDATES.validate_python(booking_candidates)
            if validated_booking:
                await asyncio.to_thread(
                    self.profiles.apply_booking_signals,
                    booking_id,
                    validated_booking,
                    source_participant=speaker_role,
                    source_ref=conversation_id,
                )
            elif booking_id:
                await asyncio.to_thread(self.profiles.invalidate_booking_profile_summary, booking_id)
        except Exception:
            logger.exception(
                "profile.queue.sql_fallback_failed trace_id=%s booking_id=%s reason=%s",
                trace_id,
                booking_id,
                reason,
            )
            return False

        logger.info(
            "profile.queue.sql_fallback_completed trace_id=%s booking_id=%s reason=%s",
            trace_id,
            booking_id,
            reason,
        )
        return True

    def start(self) -> None:
        if self.redis.available and (self._worker_task is None or self._worker_task.done()):
            self._worker_task = asyncio.create_task(self._run(), name="profile-update-worker")
            logger.info("profile.queue.worker_started queue=%s", QUEUE_NAME)

    async def stop(self) -> None:
        task = self._worker_task
        self._worker_task = None
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        logger.info("profile.queue.worker_stopped queue=%s", QUEUE_NAME)

    async def _run(self) -> None:
        while True:
            try:
                encoded = await asyncio.to_thread(self.redis.reserve_reliable, QUEUE_NAME, 1)
                if not encoded:
                    await asyncio.sleep(0)
                    continue
                await self._process(encoded)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("profile.queue.worker_error queue=%s", QUEUE_NAME)
                await asyncio.sleep(1)

    async def _process(self, encoded: str) -> None:
        try:
            payload: dict[str, Any] = json.loads(encoded)
            if "profile_updates" in payload or "booking_candidates" in payload:
                for update in payload.get("profile_updates") or []:
                    candidates = _CANDIDATES.validate_python(update.get("candidates") or [])
                    if candidates:
                        await asyncio.to_thread(self.profiles.apply, str(update["profile_id"]), candidates,
                            source_ref=str(payload.get("conversation_id") or ""), trace_id=str(payload.get("trace_id") or ""))
                booking_candidates = _BOOKING_CANDIDATES.validate_python(payload.get("booking_candidates") or [])
                if booking_candidates:
                    await asyncio.to_thread(self.profiles.apply_booking_signals, str(payload["booking_id"]), booking_candidates,
                        source_participant=str(payload.get("speaker_role") or "system"), source_ref=str(payload.get("conversation_id") or ""))
                elif payload.get("booking_id"):
                    # A durable signal can also change this booking's sales brief.
                    await asyncio.to_thread(self.profiles.invalidate_booking_profile_summary, str(payload["booking_id"]))
                await asyncio.to_thread(self.redis.ack_reliable, QUEUE_NAME, encoded)
                return
            candidates = _CANDIDATES.validate_python(payload.get("candidates") or [])
            if candidates:
                await asyncio.to_thread(self.profiles.apply, str(payload["profile_id"]), candidates,
                    source_ref=str(payload["conversation_id"]), trace_id=str(payload.get("trace_id") or ""))
            await asyncio.to_thread(self.redis.ack_reliable, QUEUE_NAME, encoded)
            logger.info("profile.queue.completed trace_id=%s conversation_id=%s profile_id=%s signal_count=%s",
                        payload.get("trace_id"), payload.get("conversation_id"), payload.get("profile_id"), len(candidates))
        except Exception:
            try:
                payload = json.loads(encoded)
            except (TypeError, json.JSONDecodeError):
                await asyncio.to_thread(self.redis.ack_reliable, QUEUE_NAME, encoded)
                return
            logger.exception("profile.queue.processing_failed queue=%s", QUEUE_NAME)
            retry_count = int(payload.get("retry_count") or 0) + 1
            payload["retry_count"] = retry_count
            await asyncio.to_thread(self.redis.retry_reliable, QUEUE_NAME, encoded, payload,
                                    dead_letter=retry_count >= MAX_RETRIES)
            if retry_count < MAX_RETRIES:
                await asyncio.sleep(min(2**retry_count, 8))
