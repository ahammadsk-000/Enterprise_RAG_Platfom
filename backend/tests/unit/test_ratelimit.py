"""Unit tests for the in-memory rate limiter."""

from __future__ import annotations

from app.core.ratelimit import InMemoryRateLimiter


def test_limiter_allows_up_to_limit_then_blocks() -> None:
    limiter = InMemoryRateLimiter(limit=3, window_s=60)
    assert [limiter.allow("client-a") for _ in range(3)] == [True, True, True]
    assert limiter.allow("client-a") is False  # 4th request blocked


def test_limiter_is_per_key() -> None:
    limiter = InMemoryRateLimiter(limit=1, window_s=60)
    assert limiter.allow("a") is True
    assert limiter.allow("b") is True  # different key has its own bucket
    assert limiter.allow("a") is False


def test_zero_limit_disables() -> None:
    limiter = InMemoryRateLimiter(limit=0)
    assert all(limiter.allow("x") for _ in range(100))
