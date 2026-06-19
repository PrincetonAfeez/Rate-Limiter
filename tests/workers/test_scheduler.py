"""Test scheduler."""

from ratelimiter.core.clock import FakeClock
from ratelimiter.workers.scheduler import MonotonicScheduler


def test_scheduler_run_pending_with_fake_clock() -> None:
    clock = FakeClock()
    scheduler = MonotonicScheduler(clock=clock)
    calls: list[str] = []
    scheduler.every(5, lambda: calls.append("ran"), name="job")

    assert scheduler.run_pending() == 0
    clock.advance(5)
    assert scheduler.run_pending() == 1
    assert calls == ["ran"]


def test_scheduler_reschedules_under_lock() -> None:
    clock = FakeClock()
    scheduler = MonotonicScheduler(clock=clock)
    calls: list[str] = []
    scheduler.every(5, lambda: calls.append("ran"), name="job")
    clock.advance(5)

    assert scheduler.run_pending() == 1
    scheduler.every(3, lambda: calls.append("new"), name="other")
    clock.advance(3)

    assert scheduler.run_pending() == 1
    assert calls == ["ran", "new"]

