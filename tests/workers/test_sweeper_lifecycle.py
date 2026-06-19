"""Test sweeper lifecycle."""

from ratelimiter.algorithms.token_bucket import TokenBucketLimiter
from ratelimiter.core.clock import FakeClock
from ratelimiter.workers.sweeper import SweeperWorker


def test_sweeper_worker_starts_stops_and_expires() -> None:
    clock = FakeClock()
    limiter = TokenBucketLimiter(capacity=1, refill_rate=1, clock=clock, ttl_seconds=0.01)
    limiter.try_acquire("user")
    clock.advance(1)

    worker = SweeperWorker(limiter.storage, interval_seconds=0.01, metrics=limiter.metrics)
    worker.start()
    worker.stop()
    worker.join(timeout=1)

    assert not worker.is_running()
    assert limiter.storage.expire() in {0, 1}

