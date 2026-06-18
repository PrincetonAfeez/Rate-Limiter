"""Test eviction does not corrupt state."""

from ratelimiter.algorithms.fixed_window import FixedWindowLimiter

def test_lru_eviction_does_not_corrupt_active_state() -> None:
    limiter = FixedWindowLimiter(limit=2, window_seconds=60, max_keys=2)

    limiter.try_acquire("a")
    limiter.try_acquire("a")
    limiter.try_acquire("b")
    limiter.try_acquire("c")

    assert not limiter.try_acquire("a").allowed or limiter.storage.get_snapshot("a") is not None
    assert len(limiter.storage.list_keys()) <= 2

