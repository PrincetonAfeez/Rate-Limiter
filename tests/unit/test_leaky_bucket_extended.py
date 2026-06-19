"""Test leaky bucket extended."""

import time

import pytest

from ratelimiter.algorithms.leaky_bucket import LeakyBucketLimiter
from ratelimiter.core.clock import FakeClock
from ratelimiter.core.errors import WorkerLifecycleError
from ratelimiter.observability.metrics import MetricsCollector
from ratelimiter.storage.state import FixedWindowState
from ratelimiter.workers.lifecycle import ManagedWorker


class _HangingWorker(ManagedWorker):
    def __init__(self) -> None:
        super().__init__(name="hanging", shutdown_timeout=0.05)

    def run(self) -> None:
        self.stop_event.wait(60)


class _FailWorker(ManagedWorker):
    def __init__(self, metrics: MetricsCollector) -> None:
        super().__init__(name="fail", metrics=metrics)

    def run(self) -> None:
        raise RuntimeError("worker boom")


def test_leaky_drain_once_missing_key_returns_zero() -> None:
    limiter = LeakyBucketLimiter(capacity=2, drain_rate=1)
    assert limiter.drain_once("missing") == 0.0


def test_leaky_drain_once_all_skips_non_leaky_states() -> None:
    clock = FakeClock()
    limiter = LeakyBucketLimiter(capacity=2, drain_rate=1, clock=clock)
    limiter.try_acquire("leaky-key")
    limiter.storage.mutate(
        "fixed-key",
        lambda now: FixedWindowState(window_start=0, count=1, last_seen=now),
        lambda state, now: None,
    )
    depths = limiter.drain_once_all()
    assert "leaky-key" in depths
    assert "fixed-key" not in depths


def test_leaky_bucket_oversized_cost_and_queue_full() -> None:
    limiter = LeakyBucketLimiter(capacity=2, drain_rate=1)
    oversized = limiter.try_acquire("user", cost=5)
    assert not oversized.allowed
    assert oversized.reason == "cost exceeds capacity"
    assert oversized.retry_after is None

    limiter = LeakyBucketLimiter(capacity=2, drain_rate=1)
    limiter.try_acquire("user")
    limiter.try_acquire("user")
    full = limiter.try_acquire("user")
    assert not full.allowed
    assert full.reason == "queue full"
    assert full.retry_after is not None
