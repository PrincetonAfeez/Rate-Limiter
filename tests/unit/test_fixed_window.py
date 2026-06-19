"""Test fixed window."""

from ratelimiter.algorithms.fixed_window import FixedWindowLimiter
from ratelimiter.core.clock import FakeClock


def test_fixed_window_resets_on_boundary() -> None:
    clock = FakeClock(start=9.9)
    limiter = FixedWindowLimiter(limit=2, window_seconds=10, clock=clock)

    assert limiter.try_acquire("user").allowed
    assert limiter.try_acquire("user").allowed
    assert not limiter.try_acquire("user").allowed

    clock.advance(0.1)
    assert limiter.try_acquire("user").allowed
    assert limiter.try_acquire("user").allowed


def test_fixed_window_cost_denial_does_not_increment() -> None:
    limiter = FixedWindowLimiter(limit=3, window_seconds=10)

    assert not limiter.try_acquire("user", cost=4).allowed
    assert limiter.try_acquire("user", cost=3).allowed

