"""TTL expiry sweeper worker."""

from __future__ import annotations

from ratelimiter.core.clock import Clock
from ratelimiter.observability.metrics import MetricsCollector
from ratelimiter.storage.base import StorageBackend
from ratelimiter.workers.lifecycle import ManagedWorker
from ratelimiter.workers.scheduler import MonotonicScheduler


class SweeperWorker(ManagedWorker):
    """Periodically asks storage to expire idle keys.

    The recurring sweep is scheduled through :class:`MonotonicScheduler`, so
    the worker decides *when* to sweep using monotonic time rather than its own
    ad-hoc bookkeeping.
    """

    def __init__(
        self,
        storage: StorageBackend,
        *,
        interval_seconds: float = 1.0,
        clock: Clock | None = None,
        metrics: MetricsCollector | None = None,
        name: str = "ratelimiter-sweeper",
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        self.storage = storage
        # The interval lives on the scheduler job; the worker loop sleeps until
        # the scheduler reports the next sweep is due.
        self._scheduler = MonotonicScheduler(clock=clock, metrics=metrics)
        self._scheduler.every(interval_seconds, self._sweep, name="expire-idle-keys")
        super().__init__(name=name, metrics=metrics)

    def _sweep(self) -> None:
        self.storage.expire()

    def run(self) -> None:
        # Sweep once immediately so idle keys expire promptly on startup, then
        # let the monotonic scheduler decide when each subsequent sweep is due.
        self._sweep()
        while not self.stop_event.is_set():
            self._scheduler.run_pending()
            self.stop_event.wait(self._scheduler.seconds_until_next_run())
