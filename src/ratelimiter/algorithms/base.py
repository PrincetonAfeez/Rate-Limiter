"""Shared algorithm helpers."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

from ratelimiter.core.clock import Clock, RealClock
from ratelimiter.core.decision import Decision
from ratelimiter.core.errors import InvalidCostError, InvalidLimitError
from ratelimiter.observability.logging import get_logger, log_event
from ratelimiter.observability.metrics import MetricsCollector
from ratelimiter.storage.base import StorageBackend
from ratelimiter.storage.memory import InMemoryStorage


@dataclass(frozen=True, slots=True)
class DecisionMetrics:
    """Per-decision usage estimate handed to the metrics collector.

    ``current_usage`` is the amount currently *consumed* against the limit:
    tokens spent for token bucket, the window count for fixed/sliding windows,
    and the queue depth for leaky bucket. Reporting one consistent
    "used" quantity keeps metrics comparable across algorithms.
    """

    current_usage: float
    queue_depth: float | None = None


class BaseLimiter:
    """Common setup for synchronous limiters."""

    algorithm = "base"

    def __init__(
        self,
        *,
        clock: Clock | None = None,
        storage: StorageBackend | None = None,
        metrics: MetricsCollector | None = None,
        ttl_seconds: float | None = None,
        max_keys: int | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.clock = clock or RealClock()
        self.metrics = metrics or MetricsCollector(self.clock)
        self.storage = storage or InMemoryStorage(
            clock=self.clock,
            ttl_seconds=ttl_seconds,
            max_keys=max_keys,
            metrics=self.metrics,
        )
        self.logger = logger or get_logger(f"ratelimiter.{self.algorithm}")

    @staticmethod
    def _validate_positive(name: str, value: float) -> None:
        if value <= 0:
            raise InvalidLimitError(f"{name} must be positive")

    @staticmethod
    def _validate_non_negative(name: str, value: float) -> None:
        if value < 0:
            raise InvalidLimitError(f"{name} must not be negative")

    @staticmethod
    def _validate_cost(cost: int | float) -> float:
        cost_value = float(cost)
        if not math.isfinite(cost_value):
            raise InvalidCostError("cost must be a finite number")
        if cost_value <= 0:
            raise InvalidCostError("cost must be positive")
        return cost_value

    @staticmethod
    def _non_negative(value: float | None) -> float | None:
        if value is None:
            return None
        return max(0.0, value)

    def _record_decision(self, key: str, decision: Decision, metrics: DecisionMetrics) -> Decision:
        self.metrics.record_decision(
            key,
            decision,
            current_usage=metrics.current_usage,
            queue_depth=metrics.queue_depth,
        )
        log_event(
            self.logger,
            "decision",
            key=key,
            algorithm=decision.algorithm,
            allowed=decision.allowed,
            remaining=decision.remaining,
            retry_after=decision.retry_after,
            reset_after=decision.reset_after,
            reason=decision.reason,
            level=logging.INFO if decision.allowed else logging.WARNING,
        )
        return decision

