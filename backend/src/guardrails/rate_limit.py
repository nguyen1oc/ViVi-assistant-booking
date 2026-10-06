from __future__ import annotations

import hashlib
import math
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from threading import Lock


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int = 0


class SlidingWindowRateLimiter:
    """Small process-local limiter used in addition to gateway protection."""

    def __init__(self, *, now: Callable[[], float] = time.monotonic) -> None:
        self._now = now
        self._events: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, bucket: str, subject: str, *, limit: int, window_seconds: int) -> RateLimitDecision:
        now = self._now()
        cutoff = now - window_seconds
        key = (bucket, self._subject_digest(subject))
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                retry_after = max(1, math.ceil(events[0] + window_seconds - now))
                return RateLimitDecision(False, retry_after)
            events.append(now)
            return RateLimitDecision(True)

    def clear(self) -> None:
        with self._lock:
            self._events.clear()

    @staticmethod
    def _subject_digest(subject: str) -> str:
        return hashlib.sha256(subject.encode("utf-8")).hexdigest()


@lru_cache
def get_rate_limiter() -> SlidingWindowRateLimiter:
    return SlidingWindowRateLimiter()
