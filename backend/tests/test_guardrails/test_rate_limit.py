from src.guardrails.rate_limit import SlidingWindowRateLimiter


def test_sliding_window_rate_limiter_blocks_and_recovers_without_storing_raw_subject():
    current = [100.0]
    limiter = SlidingWindowRateLimiter(now=lambda: current[0])

    assert limiter.check("chat", "user@example.com", limit=2, window_seconds=60).allowed is True
    assert limiter.check("chat", "user@example.com", limit=2, window_seconds=60).allowed is True
    blocked = limiter.check("chat", "user@example.com", limit=2, window_seconds=60)
    assert blocked.allowed is False
    assert blocked.retry_after_seconds == 60
    assert "user@example.com" not in repr(limiter._events)

    current[0] = 161.0

    assert limiter.check("chat", "user@example.com", limit=2, window_seconds=60).allowed is True
