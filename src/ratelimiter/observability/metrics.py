"""Thread-safe metrics snapshots."""

from __future__ import annotations

import threading
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import Any

from ratelimiter.core.clock import Clock, RealClock
from ratelimiter.core.decision import Decision


@dataclass(slots=True)
class KeyMetrics:
    allowed_count: int = 0
    denied_count: int = 0
    current_usage: float = 0.0
    queue_depth: float | None = None
    last_decision_time: float | None = None
    last_denial_reason: str | None = None
    last_retry_after: float | None = None
    last_reset_after: float | None = None

    @property
    def denial_rate(self) -> float:
        total = self.allowed_count + self.denied_count
        return 0.0 if total == 0 else self.denied_count / total

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["denial_rate"] = self.denial_rate
        return data


@dataclass(slots=True)
class GlobalMetrics:
    total_allowed: int = 0
    total_denied: int = 0
    evicted_keys: int = 0
    expired_keys: int = 0
    worker_starts: int = 0
    worker_stops: int = 0
    worker_errors: int = 0
    approximate_memory_bytes: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MetricsCollector:
    """Owns metrics updates and safe snapshots."""

    def __init__(self, clock: Clock | None = None) -> None:
        self._clock = clock or RealClock()
        self._global = GlobalMetrics()
        self._keys: dict[str, KeyMetrics] = {}
        self._lock = threading.RLock()

    def record_decision(
        self,
        key: str,
        decision: Decision,
        *,
        current_usage: float,
        queue_depth: float | None = None,
    ) -> None:
        with self._lock:
            metrics = self._keys.setdefault(key, KeyMetrics())
            if decision.allowed:
                metrics.allowed_count += 1
                self._global.total_allowed += 1
            else:
                metrics.denied_count += 1
                metrics.last_denial_reason = decision.reason
                self._global.total_denied += 1
            metrics.current_usage = current_usage
            metrics.queue_depth = queue_depth
            metrics.last_decision_time = self._clock.now()
            metrics.last_retry_after = decision.retry_after
            metrics.last_reset_after = decision.reset_after

    def forget(self, key: str) -> None:
        """Drop per-key metrics for a single key (e.g. after eviction)."""

        with self._lock:
            self._keys.pop(key, None)

    def forget_many(self, keys: Iterable[str]) -> None:
        """Drop per-key metrics for several keys at once.

        Storage calls this when keys are expired, evicted, or reset so the
        per-key metrics table stays bounded alongside the state it describes,
        and ``total_keys`` reflects keys that are actually still tracked.
        """

        with self._lock:
            for key in keys:
                self._keys.pop(key, None)

    def record_evicted(self, count: int = 1) -> None:
        if count <= 0:
            return
        with self._lock:
            self._global.evicted_keys += count

    def record_expired(self, count: int = 1) -> None:
        if count <= 0:
            return
        with self._lock:
            self._global.expired_keys += count

    def record_worker_start(self) -> None:
        with self._lock:
            self._global.worker_starts += 1

    def record_worker_stop(self) -> None:
        with self._lock:
            self._global.worker_stops += 1

    def record_worker_error(self) -> None:
        with self._lock:
            self._global.worker_errors += 1

    def set_memory_estimate(self, approximate_bytes: int) -> None:
        with self._lock:
            self._global.approximate_memory_bytes = approximate_bytes

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            # total_keys reflects keys currently tracked, computed at read time
            # so it stays accurate after expiry/eviction prune the table. It is
            # written into the returned dict rather than back onto self._global,
            # so reading a snapshot does not mutate collector state.
            global_data = self._global.to_dict()
            global_data["total_keys"] = len(self._keys)
            return {
                "global": global_data,
                "keys": {key: metrics.to_dict() for key, metrics in self._keys.items()},
            }

