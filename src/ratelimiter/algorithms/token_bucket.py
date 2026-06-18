"""Token bucket limiter."""

from __future__ import annotations

from typing import cast

from ratelimiter.algorithms.base import BaseLimiter, DecisionMetrics
from ratelimiter.core.clock import Clock
from ratelimiter.core.decision import Decision
from ratelimiter.observability.metrics import MetricsCollector
from ratelimiter.storage.base import StorageBackend
from ratelimiter.storage.state import TokenBucketState


class TokenBucketLimiter(BaseLimiter):
    """Allow bursts up to capacity and refill tokens at a steady rate."""

    algorithm = "token"

    def __init__(
        self,
        *,
        capacity: int | float,
        refill_rate: int | float,
        clock: Clock | None = None,
        storage: StorageBackend | None = None,
        metrics: MetricsCollector | None = None,
        ttl_seconds: float | None = None,
        max_keys: int | None = None,
    ) -> None:
        self.capacity = float(capacity)
        self.refill_rate = float(refill_rate)
        self._validate_positive("capacity", self.capacity)
        self._validate_non_negative("refill_rate", self.refill_rate)
        super().__init__(
            clock=clock,
            storage=storage,
            metrics=metrics,
            ttl_seconds=ttl_seconds,
            max_keys=max_keys,
        )

    def try_acquire(self, key: str, cost: int | float = 1) -> Decision:
        cost_value = self._validate_cost(cost)

        def factory(now: float) -> TokenBucketState:
            return TokenBucketState(tokens=self.capacity, last_refill=now, last_seen=now)

        def mutate(raw_state: object, now: float) -> tuple[Decision, DecisionMetrics]:
            state = cast(TokenBucketState, raw_state)
            elapsed = max(0.0, now - state.last_refill)
            if self.refill_rate > 0:
                state.tokens = min(self.capacity, state.tokens + elapsed * self.refill_rate)
            state.last_refill = now
            state.last_seen = now

            if cost_value <= state.tokens:
                state.tokens -= cost_value
                reset_after = (
                    None
                    if self.refill_rate == 0 or state.tokens >= self.capacity
                    else (self.capacity - state.tokens) / self.refill_rate
                )
                decision = Decision(
                    allowed=True,
                    remaining=state.tokens,
                    retry_after=None,
                    reset_after=self._non_negative(reset_after),
                    limit=self.capacity,
                    algorithm=self.algorithm,
                    reason="allowed",
                )
            else:
                # A cost larger than capacity can never succeed, so refilling
                # will not help: report it as such with no retry_after instead
                # of a misleading "wait N seconds" that would still be denied.
                impossible = cost_value > self.capacity
                missing = cost_value - state.tokens
                retry_after = (
                    None if (self.refill_rate == 0 or impossible) else missing / self.refill_rate
                )
                reset_after = (
                    None
                    if self.refill_rate == 0
                    else (self.capacity - min(self.capacity, state.tokens)) / self.refill_rate
                )
                decision = Decision(
                    allowed=False,
                    remaining=state.tokens,
                    retry_after=self._non_negative(retry_after),
                    reset_after=self._non_negative(reset_after),
                    limit=self.capacity,
                    algorithm=self.algorithm,
                    reason="cost exceeds capacity" if impossible else "not enough tokens",
                )
            return decision, DecisionMetrics(current_usage=self.capacity - state.tokens)

        decision, metrics = self.storage.mutate(key, factory, mutate)
        return self._record_decision(key, decision, metrics)

