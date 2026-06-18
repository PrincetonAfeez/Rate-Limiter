"""Autonomous leaky bucket drain worker."""

from __future__ import annotations

from ratelimiter.algorithms.leaky_bucket import LeakyBucketLimiter
from ratelimiter.observability.logging import log_event
from ratelimiter.observability.metrics import MetricsCollector
from ratelimiter.workers.lifecycle import ManagedWorker


class LeakyBucketDrainWorker(ManagedWorker):
    """Periodically drains every known key in a leaky bucket limiter."""

    def __init__(
        self,
        limiter: LeakyBucketLimiter,
        *,
        interval_seconds: float = 0.1,
        metrics: MetricsCollector | None = None,
        name: str = "ratelimiter-leaky-drain",
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        self.limiter = limiter
        self.interval_seconds = interval_seconds
        super().__init__(name=name, metrics=metrics or limiter.metrics)

    def run(self) -> None:
        while not self.stop_event.is_set():
            depths = self.limiter.drain_once_all()
            if depths:
                log_event(self.logger, "leaky_bucket.drained", keys=len(depths))
            self.stop_event.wait(self.interval_seconds)

