from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError

from src.agents.trace import error_details, message_to_log, trace_async_operation, trace_event
from src.database.redis_client import RedisClient

logger = logging.getLogger("profile.signal_repair")
QUEUE_NAME = "post-booking-signal-repair-v1"
MAX_RETRIES = 3


class PostBookingSignalRepairQueue:
    """Durably repair a missed/failed post-booking signal outside the chat path."""

    def __init__(self, redis: RedisClient) -> None:
        self.redis = redis
        self._worker_task: asyncio.Task[None] | None = None

    async def enqueue(
        self,
        *,
        trace_id: str,
        conversation_id: str,
        profile_id: str,
        user_message: str,
        profile_sections: dict[str, Any],
        booking_context: dict[str, Any],
        participant_context: dict[str, Any],
        reason: str,
        prior_tool_error: dict[str, Any] | None = None,
    ) -> bool:
        if not self.redis.available:
            trace_event("post_booking_signal_repair.enqueue_failed", trace_id=trace_id, reason="redis_unavailable")
            return False
        payload = {
            "trace_id": trace_id,
            "conversation_id": conversation_id,
            "profile_id": profile_id,
            "user_message": user_message,
            "profile_sections": profile_sections,
            "booking_context": booking_context,
            "participant_context": participant_context,
            "reason": reason,
            "prior_tool_error": prior_tool_error or {},
            "retry_count": 0,
        }
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        dedupe_key = hashlib.sha256(canonical.encode()).hexdigest()
        try:
            queued = await asyncio.wait_for(
                asyncio.to_thread(self.redis.enqueue_reliable, QUEUE_NAME, payload, dedupe_key=dedupe_key),
                timeout=0.5,
            )
        except TimeoutError:
            queued = False
            reason = "redis_enqueue_timeout"
        if queued:
            self.start()
            trace_event("post_booking_signal_repair.enqueued", trace_id=trace_id, reason=reason)
        else:
            trace_event("post_booking_signal_repair.enqueue_failed", trace_id=trace_id, reason=reason)
        return queued

    def start(self) -> None:
        if self.redis.available and (self._worker_task is None or self._worker_task.done()):
            self._worker_task = asyncio.create_task(self._run(), name="post-booking-signal-repair-worker")
            logger.info("post_booking_signal_repair.worker_started queue=%s", QUEUE_NAME)

    async def stop(self) -> None:
        task = self._worker_task
        self._worker_task = None
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        logger.info("post_booking_signal_repair.worker_stopped queue=%s", QUEUE_NAME)

    async def _run(self) -> None:
        while True:
            try:
                encoded = await asyncio.to_thread(self.redis.reserve_reliable, QUEUE_NAME, 1)
                if encoded:
                    await self._process(encoded)
                else:
                    await asyncio.sleep(0)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("post_booking_signal_repair.worker_error queue=%s", QUEUE_NAME)
                await asyncio.sleep(1)

    async def _process(self, encoded: str) -> None:
        payload: dict[str, Any] = {}
        trace_id = ""
        try:
            payload = json.loads(encoded)
            trace_id = str(payload.get("trace_id") or "")
            trace_event(
                "post_booking_signal_repair.started",
                trace_id=trace_id,
                reason=payload.get("reason"),
                retry_count=payload.get("retry_count", 0),
            )
            await self._repair(payload)
            await asyncio.to_thread(self.redis.ack_reliable, QUEUE_NAME, encoded)
            trace_event("post_booking_signal_repair.completed", trace_id=trace_id)
        except Exception as exc:
            logger.exception("post_booking_signal_repair.failed trace_id=%s", trace_id)
            trace_event("post_booking_signal_repair.failed", trace_id=trace_id, **error_details(exc))
            retry_count = int(payload.get("retry_count") or 0) + 1
            payload["retry_count"] = retry_count
            await asyncio.to_thread(
                self.redis.retry_reliable,
                QUEUE_NAME,
                encoded,
                payload,
                dead_letter=retry_count >= MAX_RETRIES,
            )
            trace_event(
                "post_booking_signal_repair.retry_scheduled",
                trace_id=trace_id,
                retry_count=retry_count,
                dead_letter=retry_count >= MAX_RETRIES,
            )
            if retry_count < MAX_RETRIES:
                await asyncio.sleep(min(2**retry_count, 8))

    async def _repair(self, payload: dict[str, Any]) -> None:
        # Imports stay lazy to avoid a dependencies -> worker -> tool import cycle.
        from src.agents.tools.update_post_booking_signals.tool import (
            queue_post_booking_signals,
            update_post_booking_signals,
        )
        from src.services.llm import get_llm
        from src.services.profile.models import BookingSignalCandidate, ProfileSignalCandidate

        trace_id = str(payload.get("trace_id") or "")
        llm = get_llm()
        if llm is None:
            raise RuntimeError("LLM_NOT_CONFIGURED")
        prompt = (
            "You repair a missing post-booking signal extraction. Call update_post_booking_signals exactly once. "
            "Use only facts directly supported by the current user message. Return no user-visible answer. "
            "For registered keys, category must be the category contract, never the key name.\n\n"
            f"USER PROFILE CONTEXT:\n{json.dumps(payload.get('profile_sections') or {}, ensure_ascii=False)}\n\n"
            f"BOOKING CONTEXT:\n{json.dumps(payload.get('booking_context') or {}, ensure_ascii=False)}\n\n"
            f"CURRENT PARTICIPANT:\n{json.dumps(payload.get('participant_context') or {}, ensure_ascii=False)}"
        )
        response = await trace_async_operation(
            "llm.post_booking_signal_repair.background",
            trace_id=trace_id,
            input={"reason": payload.get("reason"), "tool": update_post_booking_signals.name},
            awaitable=llm.bind_tools([update_post_booking_signals], tool_choice=update_post_booking_signals.name).ainvoke(
                [SystemMessage(content=prompt), HumanMessage(content=str(payload.get("user_message") or ""))]
            ),
        )
        call = next((item for item in response.tool_calls or [] if item.get("name") == update_post_booking_signals.name), None)
        if not call:
            raise RuntimeError("SIGNAL_REPAIR_TOOL_CALL_MISSING")
        args = call.get("args") or {}
        try:
            profile_signals = [ProfileSignalCandidate.model_validate(item) for item in args.get("profile_signals") or []]
            booking_signals = [BookingSignalCandidate.model_validate(item) for item in args.get("booking_signals") or []]
        except ValidationError as exc:
            trace_event("post_booking_signal_repair.validation_failed", trace_id=trace_id, errors=exc.errors())
            raise
        trace_event(
            "post_booking_signal_repair.extracted",
            trace_id=trace_id,
            tool_call=message_to_log(response),
            profile_signal_count=len(profile_signals),
            booking_signal_count=len(booking_signals),
        )
        result = await queue_post_booking_signals(
            profile_signals=profile_signals,
            booking_signals=booking_signals,
            profile_id=str(payload.get("profile_id") or ""),
            metadata={"trace_id": trace_id, "conversation_id": str(payload.get("conversation_id") or "")},
            participant_context=dict(payload.get("participant_context") or {}),
            current_user_message=str(payload.get("user_message") or ""),
        )
        if result.get("status") == "unavailable":
            raise RuntimeError("PROFILE_SIGNAL_QUEUE_UNAVAILABLE")
