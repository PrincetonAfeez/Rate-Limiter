"""Test scheduler extended."""

import pytest

from ratelimiter.core.clock import FakeClock
from ratelimiter.observability.metrics import MetricsCollector
from ratelimiter.workers.scheduler import MonotonicScheduler


def test_scheduler_rejects_non_positive_interval() -> None:
    scheduler = MonotonicScheduler(clock=FakeClock())
    with pytest.raises(ValueError, match="interval_seconds"):
        scheduler.every(0, lambda: None, name="bad")


def test_scheduler_records_error_when_callback_fails() -> None:
    clock = FakeClock()
    metrics = MetricsCollector(clock)
    scheduler = MonotonicScheduler(clock=clock, metrics=metrics)

    def boom() -> None:
        raise RuntimeError("scheduled failure")

    scheduler.every(1, boom, name="boom")
    clock.advance(1)
    assert scheduler.run_pending() == 1
    assert metrics.snapshot()["global"]["worker_errors"] == 1


def test_scheduler_seconds_until_next_run_with_no_jobs() -> None:
    scheduler = MonotonicScheduler(clock=FakeClock())
    assert scheduler.seconds_until_next_run() == 0.1


def test_scheduler_seconds_until_next_run_before_due() -> None:
    clock = FakeClock(start=0)
    scheduler = MonotonicScheduler(clock=clock)
    scheduler.every(10, lambda: None, name="later")
    wait = scheduler.seconds_until_next_run()
    assert 0.001 <= wait <= 10
