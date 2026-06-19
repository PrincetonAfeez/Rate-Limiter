"""Test leaky drain worker."""

import time

from ratelimiter.algorithms.leaky_bucket import LeakyBucketLimiter
from ratelimiter.workers.leaky_drain_worker import LeakyBucketDrainWorker


def test_leaky_drain_worker_reduces_queue_and_stops() -> None:
    limiter = LeakyBucketLimiter(capacity=2, drain_rate=100)
    limiter.try_acquire("user")
    limiter.try_acquire("user")

    worker = LeakyBucketDrainWorker(limiter, interval_seconds=0.01)
    worker.start()
    time.sleep(0.05)
    worker.stop()
    worker.join(timeout=1)

    assert not worker.is_running()
    snapshot = limiter.storage.get_snapshot("user")
    assert snapshot is not None
    assert snapshot.state["queue_depth"] < 2

