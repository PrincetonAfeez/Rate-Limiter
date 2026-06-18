"""Intentionally unsafe token bucket implementation for race demos."""

from __future__ import annotations

import time

from ratelimiter.algorithms.base import BaseLimiter
from ratelimiter.core.clock import Clock, RealClock
from ratelimiter.core.decision import Decision


class UnsafeTokenBucketLimiter:
    """Deliberately uses check-then-act without a lock."""

    algorithm = "unsafe-token"

    def __init__(
        self,
        *,
        capacity: int | float,
        refill_rate: int | float,
        clock: Clock | None = None,
        race_delay: float = 0.001,
    ) -> None:
        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate)
        self.clock = clock or RealClock()
        self.race_delay = race_delay
        self._tokens: dict[str, float] = {}
        self._last_refill: dict[str, float] = {}

    def try_acquire(self, key: str, cost: int | float = 1) -> Decision:
        cost_value = BaseLimiter._validate_cost(cost)
        now = self.clock.now()
        tokens = self._tokens.get(key, self.capacity)
        last_refill = self._last_refill.get(key, now)
        elapsed = max(0.0, now - last_refill)
        tokens = min(self.capacity, tokens + elapsed * self.refill_rate)

        if cost_value > self.capacity:
            return Decision(
                allowed=False,
                remaining=tokens,
                retry_after=None,
                reset_after=None,
                limit=self.capacity,
                algorithm=self.algorithm,
                reason="cost exceeds capacity",
            )

        if cost_value <= tokens:
            time.sleep(self.race_delay)
            self._tokens[key] = tokens - cost_value
            self._last_refill[key] = now
            return Decision(
                allowed=True,
                remaining=tokens - cost_value,
                retry_after=None,
                reset_after=None,
                limit=self.capacity,
                algorithm=self.algorithm,
                reason="allowed by unsafe check-then-act path",
            )

        impossible = self.refill_rate <= 0
        retry_after = None if impossible else (cost_value - tokens) / self.refill_rate
        self._tokens[key] = tokens
        self._last_refill[key] = now
        return Decision(
            allowed=False,
            remaining=tokens,
            retry_after=retry_after,
            reset_after=retry_after,
            limit=self.capacity,
            algorithm=self.algorithm,
            reason="not enough tokens",
        )
