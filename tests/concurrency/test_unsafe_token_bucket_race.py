"""Test unsafe token bucket race."""

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from ratelimiter.algorithms.token_bucket import TokenBucketLimiter
from ratelimiter.teaching.unsafe_token_bucket import UnsafeTokenBucketLimiter


@pytest.mark.timing_dependent
def test_unsafe_token_bucket_can_over_admit() -> None:
    # Timing-dependent teaching demo: barrier-synchronized threads plus a race
    # window make the check-then-act path over-admit reliably. Safe-path tests
    # prove the production limiter never does this.
    limiter = UnsafeTokenBucketLimiter(capacity=5, refill_rate=0, race_delay=0.003)
    threads = 40
    requests = 80
    barrier = threading.Barrier(threads)

    def worker(worker_index: int) -> int:
        allowed = 0
        barrier.wait()
        for index in range(worker_index, requests, threads):
            if limiter.try_acquire("hot").allowed:
                allowed += 1
        return allowed

    with ThreadPoolExecutor(max_workers=threads) as executor:
        total_allowed = sum(executor.map(worker, range(threads)))

    assert total_allowed > 5


def test_safe_token_bucket_never_over_admits_same_workload() -> None:
    limiter = TokenBucketLimiter(capacity=5, refill_rate=0)
    threads = 40
    requests = 80
    barrier = threading.Barrier(threads)

    def worker(worker_index: int) -> int:
        allowed = 0
        barrier.wait()
        for index in range(worker_index, requests, threads):
            if limiter.try_acquire("hot").allowed:
                allowed += 1
        return allowed

    with ThreadPoolExecutor(max_workers=threads) as executor:
        total_allowed = sum(executor.map(worker, range(threads)))

    assert total_allowed == 5
