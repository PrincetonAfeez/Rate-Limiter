"""Test unsafe race failure."""

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from ratelimiter.teaching.unsafe_fixed_window import UnsafeFixedWindowLimiter


@pytest.mark.timing_dependent
def test_unsafe_fixed_window_can_over_admit() -> None:
    # Timing-dependent teaching demo: barrier-synchronized threads plus a race
    # window make the check-then-act path over-admit reliably. Safe-path tests
    # prove the production limiter never does this.
    limiter = UnsafeFixedWindowLimiter(limit=5, window_seconds=60, race_delay=0.003)
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
