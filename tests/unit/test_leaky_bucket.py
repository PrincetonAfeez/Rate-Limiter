"""Test leaky bucket."""

from ratelimiter.algorithms.leaky_bucket import LeakyBucketLimiter
from ratelimiter.core.clock import FakeClock


def test_leaky_bucket_queue_and_drain() -> None:
    clock = FakeClock()
    limiter = LeakyBucketLimiter(capacity=2, drain_rate=1, clock=clock)

    assert limiter.try_acquire("user").allowed
    assert limiter.try_acquire("user").allowed
    denied = limiter.try_acquire("user")
    assert not denied.allowed
    assert denied.retry_after == 1

    clock.advance(1)
    assert limiter.try_acquire("user").allowed


def test_leaky_bucket_drain_once_all() -> None:
    clock = FakeClock()
    limiter = LeakyBucketLimiter(capacity=2, drain_rate=1, clock=clock)

    limiter.try_acquire("a")
    limiter.try_acquire("b")
    clock.advance(1)

    depths = limiter.drain_once_all()

    assert depths == {"a": 0.0, "b": 0.0}

