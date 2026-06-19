"""Test worker validation."""

import pytest

from ratelimiter.core.clock import FakeClock
from ratelimiter.storage.memory import InMemoryStorage
from ratelimiter.workers.leaky_drain_worker import LeakyBucketDrainWorker
from ratelimiter.workers.sweeper import SweeperWorker


def test_leaky_drain_worker_rejects_non_positive_interval() -> None:
    from ratelimiter.algorithms.leaky_bucket import LeakyBucketLimiter

    limiter = LeakyBucketLimiter(capacity=1, drain_rate=1)
    with pytest.raises(ValueError, match="interval_seconds"):
        LeakyBucketDrainWorker(limiter, interval_seconds=0)


def test_sweeper_worker_rejects_non_positive_interval() -> None:
    storage = InMemoryStorage(clock=FakeClock())
    with pytest.raises(ValueError, match="interval_seconds"):
        SweeperWorker(storage, interval_seconds=-1)
