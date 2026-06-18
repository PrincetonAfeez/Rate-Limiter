"""Monotonic repeated-job scheduler."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from threading import RLock

from ratelimiter.core.clock import Clock, RealClock
from ratelimiter.observability.logging import log_event
from ratelimiter.observability.metrics import MetricsCollector
from ratelimiter.workers.lifecycle import ManagedWorker


@dataclass(slots=True)
class RepeatedJob:
    name: str
    interval_seconds: float
    callback: Callable[[], None]
    next_run: float


class MonotonicScheduler(ManagedWorker):
    """Run repeated jobs according to monotonic time."""

    def __init__(
        self,
        *,
        clock: Clock | None = None,
        metrics: MetricsCollector | None = None,
        name: str = "ratelimiter-scheduler",
    ) -> None:
        self.clock = clock or RealClock()
        self._jobs: list[RepeatedJob] = []
        self._jobs_lock = RLock()
        super().__init__(name=name, metrics=metrics)

    def every(self, interval_seconds: float, callback: Callable[[], None], *, name: str) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        with self._jobs_lock:
            self._jobs.append(
                RepeatedJob(
                    name=name,
                    interval_seconds=interval_seconds,
                    callback=callback,
                    next_run=self.clock.now() + interval_seconds,
                )
            )

    def run_pending(self) -> int:
        now = self.clock.now()
        with self._jobs_lock:
            due = [job for job in self._jobs if job.next_run <= now]
            ran = 0
            for job in due:
                try:
                    job.callback()
                except Exception:
                    if self.metrics is not None:
                        self.metrics.record_worker_error()
                    self.logger.exception("scheduled job failed")
                finally:
                    job.next_run = now + job.interval_seconds
                    log_event(self.logger, "scheduler.job_ran", job=job.name)
                    ran += 1
            return ran

    def run(self) -> None:
        # Note: the loop waits on the stop event using the host's real clock,
        # so an injected FakeClock cannot fast-forward the thread loop. Drive
        # run_pending() directly (as the tests do) for deterministic schedules.
        while not self.stop_event.is_set():
            self.run_pending()
            self.stop_event.wait(self.seconds_until_next_run())

    def seconds_until_next_run(self) -> float:
        with self._jobs_lock:
            if not self._jobs:
                return 0.1
            now = self.clock.now()
            return max(0.001, min(max(0.0, job.next_run - now) for job in self._jobs))

