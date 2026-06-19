"""Test scheduler run loop."""

import threading
import time

from ratelimiter.core.clock import FakeClock
from ratelimiter.workers.scheduler import MonotonicScheduler


def test_scheduler_run_loop_executes_until_stopped() -> None:
    clock = FakeClock()
    scheduler = MonotonicScheduler(clock=clock)
    calls: list[str] = []

    scheduler.every(0.001, lambda: calls.append("tick"), name="tick")
    scheduler.start()
    clock.advance(0.01)
    time.sleep(0.05)
    scheduler.stop()
    scheduler.join(timeout=1)

    assert calls
