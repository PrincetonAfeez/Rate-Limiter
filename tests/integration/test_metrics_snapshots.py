"""Test metrics snapshots."""

from ratelimiter.algorithms.token_bucket import TokenBucketLimiter
from ratelimiter.core.clock import FakeClock


def test_metrics_snapshot_counts_decisions() -> None:
    limiter = TokenBucketLimiter(capacity=1, refill_rate=0)

    assert limiter.try_acquire("user").allowed
    assert not limiter.try_acquire("user").allowed

    snapshot = limiter.metrics.snapshot()
    assert snapshot["global"]["total_allowed"] == 1
    assert snapshot["global"]["total_denied"] == 1
    assert snapshot["keys"]["user"]["denied_count"] == 1


def test_metrics_forget_expired_keys_and_report_active_total() -> None:
    clock = FakeClock()
    limiter = TokenBucketLimiter(capacity=5, refill_rate=1, clock=clock, ttl_seconds=10)

    for key in ("a", "b", "c"):
        limiter.try_acquire(key)
    assert limiter.metrics.snapshot()["global"]["total_keys"] == 3

    clock.advance(100)  # all keys now idle past the TTL
    assert limiter.storage.expire() == 3

    snapshot = limiter.metrics.snapshot()
    # Per-key metrics are pruned with the state they describe, so total_keys
    # reflects active keys rather than every key ever seen.
    assert snapshot["global"]["total_keys"] == 0
    assert snapshot["keys"] == {}


def test_metrics_record_retry_and_reset_hints() -> None:
    limiter = TokenBucketLimiter(capacity=1, refill_rate=1)

    limiter.try_acquire("user")
    denied = limiter.try_acquire("user")

    assert denied.retry_after is not None
    metrics = limiter.metrics.snapshot()["keys"]["user"]
    assert metrics["last_retry_after"] == denied.retry_after
    assert metrics["last_reset_after"] == denied.reset_after

