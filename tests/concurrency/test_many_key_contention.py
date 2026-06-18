"""Test many key contention."""

from concurrent.futures import ThreadPoolExecutor

from fixtures.traffic_patterns import many_keys

from ratelimiter.algorithms.fixed_window import FixedWindowLimiter
from ratelimiter.core.clock import FakeClock


def test_many_keys_have_independent_limits_under_contention() -> None:
    limiter = FixedWindowLimiter(limit=3, window_seconds=60, clock=FakeClock())
    keys = [many_keys(index) for index in range(100)]

    with ThreadPoolExecutor(max_workers=32) as executor:
        decisions = list(executor.map(lambda key: (key, limiter.try_acquire(key)), keys))

    allowed_by_key: dict[str, int] = {}
    for key, decision in decisions:
        allowed_by_key[key] = allowed_by_key.get(key, 0) + int(decision.allowed)

    assert set(allowed_by_key.values()) == {3}

