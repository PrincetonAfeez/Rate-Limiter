"""Test metrics extended."""

from ratelimiter.core.clock import FakeClock
from ratelimiter.core.decision import Decision
from ratelimiter.observability.metrics import GlobalMetrics, KeyMetrics, MetricsCollector


def _decision(*, allowed: bool) -> Decision:
    return Decision(
        allowed=allowed,
        remaining=0,
        retry_after=1.0 if not allowed else None,
        reset_after=2.0,
        limit=5,
        algorithm="token",
        reason="test",
    )


def test_key_metrics_denial_rate_and_to_dict() -> None:
    metrics = KeyMetrics(allowed_count=3, denied_count=1)
    assert metrics.denial_rate == 0.25
    data = metrics.to_dict()
    assert data["denial_rate"] == 0.25
    assert data["allowed_count"] == 3


def test_global_metrics_to_dict() -> None:
    data = GlobalMetrics(total_allowed=10, worker_starts=1).to_dict()
    assert data["total_allowed"] == 10
    assert data["worker_starts"] == 1


def test_metrics_forget_and_forget_many() -> None:
    collector = MetricsCollector()
    collector.record_decision("a", _decision(allowed=True), current_usage=1)
    collector.record_decision("b", _decision(allowed=True), current_usage=1)
    collector.forget("a")
    collector.forget_many(["b", "missing"])
    assert collector.snapshot()["keys"] == {}


def test_metrics_record_evicted_and_expired_ignore_non_positive() -> None:
    collector = MetricsCollector()
    collector.record_evicted(0)
    collector.record_expired(-1)
    snapshot = collector.snapshot()["global"]
    assert snapshot["evicted_keys"] == 0
    assert snapshot["expired_keys"] == 0


def test_metrics_worker_lifecycle_and_memory_estimate() -> None:
    collector = MetricsCollector()
    collector.record_worker_start()
    collector.record_worker_stop()
    collector.record_worker_error()
    collector.set_memory_estimate(4096)
    global_metrics = collector.snapshot()["global"]
    assert global_metrics["worker_starts"] == 1
    assert global_metrics["worker_stops"] == 1
    assert global_metrics["worker_errors"] == 1
    assert global_metrics["approximate_memory_bytes"] == 4096


def test_metrics_snapshot_uses_injected_clock() -> None:
    clock = FakeClock(start=100.0)
    collector = MetricsCollector(clock)
    collector.record_decision("user", _decision(allowed=True), current_usage=1)
    assert collector.snapshot()["keys"]["user"]["last_decision_time"] == 100.0
