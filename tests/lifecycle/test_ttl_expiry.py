"""Test TTL expiry."""

from ratelimiter.algorithms.token_bucket import TokenBucketLimiter
from ratelimiter.core.clock import FakeClock

def test_idle_keys_expire_without_new_request_traffic() -> None:
    clock = FakeClock()
    limiter = TokenBucketLimiter(capacity=1, refill_rate=1, clock=clock, ttl_seconds=5)

    limiter.try_acquire("user")
    clock.advance(5)

    assert limiter.storage.expire() == 1
    assert limiter.storage.list_keys() == []

