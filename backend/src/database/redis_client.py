from __future__ import annotations

import json
import logging
from typing import Any

from src.config import get_settings

logger = logging.getLogger(__name__)


class RedisClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.enabled: bool = getattr(settings, "redis_enabled", False)
        self.url: str = getattr(settings, "redis_url", "")
        self._client: Any = None
        if self.enabled and self.url:
            try:
                import redis  # type: ignore[import-not-found,import-untyped]
                self._client = redis.from_url(self.url, decode_responses=True)
                if self.is_connected():
                    msg = f"[REDIS CONNECTED] Connected successfully to Redis at {self.url}"
                    logger.info(msg)
                    print(msg, flush=True)
                else:
                    msg = f"[REDIS WARNING] Ping failed to Redis at {self.url}. Will fallback to SQL."
                    logger.warning(msg)
                    print(msg, flush=True)
            except Exception as err:
                msg = f"[REDIS ERROR] Failed to initialize Redis client ({err}). Falling back to SQL/in-memory."
                logger.warning(msg)
                print(msg, flush=True)
                self._client = None
        else:
            msg = f"[REDIS DISABLED] redis_enabled={self.enabled}, url={self.url}"
            logger.info(msg)
            print(msg, flush=True)

    def is_connected(self) -> bool:
        if not self._client:
            return False
        try:
            return bool(self._client.ping())
        except Exception:
            return False

    @property
    def available(self) -> bool:
        return bool(self.enabled and self._client)

    def enqueue_reliable(
        self,
        queue_name: str,
        payload: dict[str, Any],
        *,
        dedupe_key: str,
        dedupe_ttl_seconds: int = 30,
    ) -> bool:
        """Atomically claim a short dedupe key and append a JSON job to Redis."""
        if not self._client:
            return False
        queue_key = f"queue:{queue_name}:pending"
        claim_key = f"queue:{queue_name}:dedupe:{dedupe_key}"
        encoded = json.dumps(payload, ensure_ascii=False)
        script = (
            "if redis.call('SET', KEYS[1], '1', 'NX', 'EX', ARGV[1]) then "
            "redis.call('LPUSH', KEYS[2], ARGV[2]); return 1 else return 0 end"
        )
        try:
            result = self._client.eval(
                script,
                2,
                claim_key,
                queue_key,
                str(dedupe_ttl_seconds),
                encoded,
            )
            # A duplicate is already queued or was processed recently, so it is
            # a successful no-op from the request path's perspective.
            return result in {0, 1}
        except Exception as err:
            logger.warning("Redis enqueue_reliable failed for %s: %s", queue_name, err)
            return False

    def reserve_reliable(self, queue_name: str, timeout_seconds: int = 1) -> str | None:
        """Move one job from pending to processing before returning it."""
        if not self._client:
            return None
        try:
            return self._client.brpoplpush(
                f"queue:{queue_name}:pending",
                f"queue:{queue_name}:processing",
                timeout=timeout_seconds,
            )
        except Exception as err:
            logger.warning("Redis reserve_reliable failed for %s: %s", queue_name, err)
            return None

    def ack_reliable(self, queue_name: str, encoded_payload: str) -> bool:
        if not self._client:
            return False
        try:
            self._client.lrem(f"queue:{queue_name}:processing", 1, encoded_payload)
            return True
        except Exception as err:
            logger.warning("Redis ack_reliable failed for %s: %s", queue_name, err)
            return False

    def retry_reliable(
        self,
        queue_name: str,
        encoded_payload: str,
        payload: dict[str, Any],
        *,
        dead_letter: bool,
    ) -> bool:
        if not self._client:
            return False
        destination = "dead" if dead_letter else "pending"
        try:
            pipeline = self._client.pipeline(transaction=True)
            pipeline.lrem(f"queue:{queue_name}:processing", 1, encoded_payload)
            pipeline.lpush(
                f"queue:{queue_name}:{destination}",
                json.dumps(payload, ensure_ascii=False),
            )
            pipeline.execute()
            return True
        except Exception as err:
            logger.warning("Redis retry_reliable failed for %s: %s", queue_name, err)
            return False

    def set_otp(self, key: str, code: str, ttl_seconds: int = 60) -> bool:
        if not self._client:
            msg = "[REDIS BYPASS] set_otp skipped, Redis not connected"
            print(msg, flush=True)
            return False
        try:
            self._client.setex(f"otp:{key}", ttl_seconds, code)
            msg = f"[REDIS SUCCESS] Stored OTP for {key} (TTL: {ttl_seconds}s)"
            logger.info(msg)
            print(msg, flush=True)
            return True
        except Exception as err:
            msg = f"[REDIS ERROR] Redis set_otp failed: {err}"
            logger.warning(msg)
            print(msg, flush=True)
            return False

    def get_otp(self, key: str) -> str | None:
        if not self._client:
            return None
        try:
            val = self._client.get(f"otp:{key}")
            if val:
                msg = f"[REDIS SUCCESS] Retrieved OTP for {key} from Redis"
                logger.info(msg)
                print(msg, flush=True)
            return val
        except Exception as err:
            msg = f"[REDIS ERROR] Redis get_otp failed: {err}"
            logger.warning(msg)
            print(msg, flush=True)
            return None

    def hold_slot(self, slot_id: str, booking_id: str, ttl_seconds: int = 300) -> bool:
        if not self._client:
            msg = "[REDIS BYPASS] hold_slot skipped, Redis not connected"
            print(msg, flush=True)
            return False
        try:
            self._client.setex(f"hold_slot:{slot_id}", ttl_seconds, booking_id)
            msg = f"[REDIS SUCCESS] Held slot {slot_id} for booking {booking_id} in Redis (TTL: {ttl_seconds}s)"
            logger.info(msg)
            print(msg, flush=True)
            return True
        except Exception as err:
            msg = f"[REDIS ERROR] Redis hold_slot failed: {err}"
            logger.warning(msg)
            print(msg, flush=True)
            return False

    def is_slot_held(self, slot_id: str) -> bool:
        if not self._client:
            return False
        try:
            return bool(self._client.exists(f"hold_slot:{slot_id}"))
        except Exception as err:
            logger.warning("Redis is_slot_held failed: %s", err)
            return False

    def delete_slot_hold(self, slot_id: str) -> bool:
        if not self._client:
            return False
        try:
            self._client.delete(f"hold_slot:{slot_id}")
            msg = f"[REDIS SUCCESS] Released slot hold for {slot_id} in Redis"
            logger.info(msg)
            print(msg, flush=True)
            return True
        except Exception as err:
            msg = f"[REDIS ERROR] Redis delete_slot_hold failed: {err}"
            logger.warning(msg)
            print(msg, flush=True)
            return False

    def release_slot_hold(self, slot_id: str) -> bool:
        if not self._client:
            return False
        try:
            self._client.delete(f"hold_slot:{slot_id}")
            return True
        except Exception as err:
            logger.warning("Redis release_slot_hold failed: %s", err)
            return False

    def set_cache(self, key: str, value: Any, ttl_seconds: int = 3600) -> bool:
        if not self._client:
            return False
        try:
            payload = json.dumps(value, ensure_ascii=False)
            self._client.setex(f"cache:{key}", ttl_seconds, payload)
            return True
        except Exception as err:
            logger.warning("Redis set_cache failed: %s", err)
            return False

    def get_cache(self, key: str) -> Any | None:
        if not self._client:
            return None
        try:
            raw = self._client.get(f"cache:{key}")
            return json.loads(raw) if raw else None
        except Exception as err:
            logger.warning("Redis get_cache failed: %s", err)
            return None


redis_client = RedisClient()
