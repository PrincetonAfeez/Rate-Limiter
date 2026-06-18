"""Intentionally unsafe fixed-window implementation for race demos."""

from __future__ import annotations

import math
import time

from ratelimiter.algorithms.base import BaseLimiter
from ratelimiter.core.clock import Clock, RealClock
from ratelimiter.core.decision import Decision


class UnsafeFixedWindowLimiter:
    """Deliberately reads and writes state without atomic protection."""

    algorithm = "unsafe-fixed-window"

    def __init__(
        self,
        *,
        limit: int | float,
        window_seconds: int | float,
        clock: Clock | None = None,
        race_delay: float = 0.001,
    ) -> None:
        self.limit = float(limit)
        self.window_seconds = float(window_seconds)
        self.clock = clock or RealClock()
        self.race_delay = race_delay
        self._counts: dict[tuple[str, float], float] = {}

    def try_acquire(self, key: str, cost: int | float = 1) -> Decision:
        cost_value = BaseLimiter._validate_cost(cost)
        now = self.clock.now()
        window_start = math.floor(now / self.window_seconds) * self.window_seconds
        bucket = (key, window_start)
        current = self._counts.get(bucket, 0.0)
        reset_after = max(0.0, window_start + self.window_seconds - now)

        if cost_value > self.limit:
            return Decision(
                allowed=False,
                remaining=max(0.0, self.limit - current),
                retry_after=None,
                reset_after=reset_after,
                limit=self.limit,
                algorithm=self.algorithm,
                reason="cost exceeds limit",
            )

        if current + cost_value <= self.limit:
            time.sleep(self.race_delay)
            self._counts[bucket] = current + cost_value
            return Decision(
                allowed=True,
                remaining=max(0.0, self.limit - (current + cost_value)),
                retry_after=None,
                reset_after=reset_after,
                limit=self.limit,
                algorithm=self.algorithm,
                reason="allowed by unsafe check-then-act path",
            )

        return Decision(
            allowed=False,
            remaining=max(0.0, self.limit - current),
            retry_after=reset_after,
            reset_after=reset_after,
            limit=self.limit,
            algorithm=self.algorithm,
            reason="window limit exceeded",
        )
