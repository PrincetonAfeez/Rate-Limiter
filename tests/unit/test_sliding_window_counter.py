"""Test sliding window counter."""

from ratelimiter.algorithms.sliding_window_counter import SlidingWindowCounterLimiter
from ratelimiter.core.clock import FakeClock


def test_sliding_window_counter_weights_previous_window() -> None:
    clock = FakeClock(start=0)
    limiter = SlidingWindowCounterLimiter(limit=4, window_seconds=10, clock=clock)

    for _ in range(4):
        assert limiter.try_acquire("user").allowed

    clock.advance(10)
    assert not limiter.try_acquire("user", cost=3).allowed

    clock.advance(5)
    assert limiter.try_acquire("user", cost=2).allowed


def test_sliding_window_counter_never_negative_retry() -> None:
    limiter = SlidingWindowCounterLimiter(limit=1, window_seconds=10)

    limiter.try_acquire("user")
    denied = limiter.try_acquire("user")

    assert denied.retry_after is not None
    assert denied.retry_after >= 0


def test_sliding_window_forgets_traffic_after_multi_window_jump() -> None:
    clock = FakeClock(start=0)
    limiter = SlidingWindowCounterLimiter(limit=2, window_seconds=10, clock=clock)

    assert limiter.try_acquire("user").allowed
    assert limiter.try_acquire("user").allowed
    assert not limiter.try_acquire("user").allowed

    clock.advance(25)
    allowed = limiter.try_acquire("user")

    assert allowed.allowed
    assert allowed.remaining == 1.0

