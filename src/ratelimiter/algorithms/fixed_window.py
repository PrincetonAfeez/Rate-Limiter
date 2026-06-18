"""Fixed window counter limiter."""

from __future__ import annotations

import math
from typing import cast

from ratelimiter.algorithms.base import BaseLimiter, DecisionMetrics
from ratelimiter.core.clock import Clock
from ratelimiter.core.decision import Decision
from ratelimiter.observability.metrics import MetricsCollector
from ratelimiter.storage.base import StorageBackend
from ratelimiter.storage.state import FixedWindowState


class FixedWindowLimiter(BaseLimiter):
    """Count requests in discrete windows."""

    algorithm = "fixed-window"

    def __init__(
        self,
        *,
        limit: int | float,
        window_seconds: int | float,
        clock: Clock | None = None,
        storage: StorageBackend | None = None,
        metrics: MetricsCollector | None = None,
        ttl_seconds: float | None = None,
        max_keys: int | None = None,
    ) -> None:
        self.limit = float(limit)
        self.window_seconds = float(window_seconds)
        self._validate_positive("limit", self.limit)
        self._validate_positive("window_seconds", self.window_seconds)
        super().__init__(
            clock=clock,
            storage=storage,
            metrics=metrics,
            ttl_seconds=ttl_seconds,
            max_keys=max_keys,
        )

    def try_acquire(self, key: str, cost: int | float = 1) -> Decision:
        cost_value = self._validate_cost(cost)

        def factory(now: float) -> FixedWindowState:
            current_window = math.floor(now / self.window_seconds) * self.window_seconds
            return FixedWindowState(window_start=current_window, count=0.0, last_seen=now)

        def mutate(raw_state: object, now: float) -> tuple[Decision, DecisionMetrics]:
            state = cast(FixedWindowState, raw_state)
            current_window = math.floor(now / self.window_seconds) * self.window_seconds
            if state.window_start != current_window:
                state.window_start = current_window
                state.count = 0.0
            state.last_seen = now
            reset_after = self._non_negative(state.window_start + self.window_seconds - now)

            if state.count + cost_value <= self.limit:
                state.count += cost_value
                decision = Decision(
                    allowed=True,
                    remaining=max(0.0, self.limit - state.count),
                    retry_after=None,
                    reset_after=reset_after,
                    limit=self.limit,
                    algorithm=self.algorithm,
                    reason="allowed",
                )
            else:
                # A cost above the per-window limit can never fit, even in a
                # fresh window, so it has no meaningful retry_after.
                impossible = cost_value > self.limit
                decision = Decision(
                    allowed=False,
                    remaining=max(0.0, self.limit - state.count),
                    retry_after=None if impossible else reset_after,
                    reset_after=reset_after,
                    limit=self.limit,
                    algorithm=self.algorithm,
                    reason="cost exceeds limit" if impossible else "window limit exceeded",
                )
            return decision, DecisionMetrics(current_usage=state.count)

        decision, metrics = self.storage.mutate(key, factory, mutate)
        return self._record_decision(key, decision, metrics)

