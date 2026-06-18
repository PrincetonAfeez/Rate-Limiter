"""Test hot key contention."""

from concurrent.futures import ThreadPoolExecutor

from fixtures.traffic_patterns import hot_key

from ratelimiter.algorithms.fixed_window import FixedWindowLimiter
from ratelimiter.core.clock import FakeClock


def test_fixed_window_hot_key_contention() -> None:
    limiter = FixedWindowLimiter(limit=15, window_seconds=60, clock=FakeClock())

    with ThreadPoolExecutor(max_workers=24) as executor:
        decisions = list(executor.map(lambda index: limiter.try_acquire(hot_key(index)), range(120)))

    assert sum(decision.allowed for decision in decisions) == 15

