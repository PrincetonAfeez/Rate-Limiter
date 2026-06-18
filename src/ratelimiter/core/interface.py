"""Public rate limiter protocol."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ratelimiter.core.decision import Decision
from ratelimiter.observability.metrics import MetricsCollector
from ratelimiter.storage.base import StorageBackend


@runtime_checkable
class RateLimiter(Protocol):
    """Shared interface implemented by all algorithms."""

    algorithm: str

    def try_acquire(self, key: str, cost: int | float = 1) -> Decision:
        """Try to consume capacity for a key and return an explanatory decision."""


@runtime_checkable
class InspectableLimiter(RateLimiter, Protocol):
    """Limiter that exposes storage and metrics for CLI inspection."""

    storage: StorageBackend
    metrics: MetricsCollector
