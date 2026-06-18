"""Sliding window counter limiter."""

from __future__ import annotations

import math
from typing import cast

from ratelimiter.algorithms.base import BaseLimiter, DecisionMetrics
from ratelimiter.core.clock import Clock
from ratelimiter.core.decision import Decision
from ratelimiter.observability.metrics import MetricsCollector
from ratelimiter.storage.base import StorageBackend
from ratelimiter.storage.state import SlidingWindowCounterState


class SlidingWindowCounterLimiter(BaseLimiter):
    """Weighted current/previous window approximation."""

    algorithm = "sliding-window-counter"

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

        def factory(now: float) -> SlidingWindowCounterState:
            current_window = math.floor(now / self.window_seconds) * self.window_seconds
            return SlidingWindowCounterState(
                window_start=current_window,
                current_count=0.0,
                previous_count=0.0,
                last_seen=now,
            )

        def mutate(raw_state: object, now: float) -> tuple[Decision, DecisionMetrics]:
            state = cast(SlidingWindowCounterState, raw_state)
            current_window = math.floor(now / self.window_seconds) * self.window_seconds
            self._roll_window(state, current_window)
            state.last_seen = now

            estimate = self._estimate(state, now)
            reset_after = self._non_negative(state.window_start + self.window_seconds - now)
            if estimate + cost_value <= self.limit:
                state.current_count += cost_value
                new_estimate = self._estimate(state, now)
                decision = Decision(
                    allowed=True,
                    remaining=max(0.0, self.limit - new_estimate),
                    retry_after=None,
                    reset_after=reset_after,
                    limit=self.limit,
                    algorithm=self.algorithm,
                    reason="allowed",
                )
                return decision, DecisionMetrics(current_usage=new_estimate)

            # A cost above the limit can never fit regardless of decay.
            impossible = cost_value > self.limit
            retry_after = None if impossible else self._retry_after(state, now, cost_value)
            decision = Decision(
                allowed=False,
                remaining=max(0.0, self.limit - estimate),
                retry_after=self._non_negative(retry_after),
                reset_after=reset_after,
                limit=self.limit,
                algorithm=self.algorithm,
                reason="cost exceeds limit" if impossible else "weighted window limit exceeded",
            )
            return decision, DecisionMetrics(current_usage=estimate)

        decision, metrics = self.storage.mutate(key, factory, mutate)
        return self._record_decision(key, decision, metrics)

    def _roll_window(self, state: SlidingWindowCounterState, current_window: float) -> None:
        if current_window <= state.window_start:
            return
        windows_passed = int((current_window - state.window_start) / self.window_seconds)
        state.previous_count = state.current_count if windows_passed == 1 else 0.0
        state.current_count = 0.0
        state.window_start = current_window

    def _estimate(self, state: SlidingWindowCounterState, now: float) -> float:
        elapsed = max(0.0, now - state.window_start)
        weight = max(0.0, (self.window_seconds - elapsed) / self.window_seconds)
        return state.current_count + state.previous_count * weight

    def _retry_after(self, state: SlidingWindowCounterState, now: float, cost: float) -> float:
        elapsed = max(0.0, now - state.window_start)
        estimate = self._estimate(state, now)
        if state.previous_count <= 0 or state.current_count + cost > self.limit:
            return max(0.0, self.window_seconds - elapsed)
        excess = estimate + cost - self.limit
        decay_per_second = state.previous_count / self.window_seconds
        return max(0.0, excess / decay_per_second)

