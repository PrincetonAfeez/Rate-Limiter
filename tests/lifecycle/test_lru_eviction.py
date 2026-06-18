"""Test LRU eviction."""

from ratelimiter.algorithms.token_bucket import TokenBucketLimiter

def test_lru_cap_bounds_memory() -> None:
    limiter = TokenBucketLimiter(capacity=10, refill_rate=1, max_keys=2)

    limiter.try_acquire("a")
    limiter.try_acquire("b")
    limiter.try_acquire("c")

    assert limiter.storage.list_keys() == ["b", "c"]
    snapshot = limiter.metrics.snapshot()
    assert snapshot["global"]["evicted_keys"] == 1
    # The evicted key's per-key metrics are pruned alongside its state.
    assert "a" not in snapshot["keys"]
    assert snapshot["global"]["total_keys"] == 2

