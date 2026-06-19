"""Test token bucket."""

from ratelimiter.algorithms.token_bucket import TokenBucketLimiter
from ratelimiter.core.clock import FakeClock


def test_token_bucket_burst_refill_and_retry_after() -> None:
    clock = FakeClock()
    limiter = TokenBucketLimiter(capacity=3, refill_rate=1, clock=clock)

    assert limiter.try_acquire("user").allowed
    assert limiter.try_acquire("user").allowed
    assert limiter.try_acquire("user").allowed

    denied = limiter.try_acquire("user")
    assert not denied.allowed
    assert denied.retry_after == 1
    assert denied.reset_after == 3

    clock.advance(1)
    allowed = limiter.try_acquire("user")
    assert allowed.allowed
    assert allowed.remaining == 0


def test_token_bucket_supports_cost() -> None:
    limiter = TokenBucketLimiter(capacity=5, refill_rate=1)

    decision = limiter.try_acquire("user", cost=3)

    assert decision.allowed
    assert decision.remaining == 2


def test_token_bucket_cost_above_capacity_has_no_retry_after() -> None:
    limiter = TokenBucketLimiter(capacity=5, refill_rate=1)

    decision = limiter.try_acquire("user", cost=10)

    # A request larger than capacity can never succeed, so there is no honest
    # retry_after to offer.
    assert not decision.allowed
    assert decision.retry_after is None
    assert decision.reason == "cost exceeds capacity"

