"""Leaky bucket limiter."""

from __future__ import annotations

from typing import cast

from ratelimiter.algorithms.base import BaseLimiter, DecisionMetrics
from ratelimiter.core.clock import Clock
from ratelimiter.core.decision import Decision
from ratelimiter.observability.metrics import MetricsCollector
from ratelimiter.storage.base import StorageBackend
from ratelimiter.storage.state import LeakyBucketState


class LeakyBucketLimiter(BaseLimiter):
    """Queue-like limiter that drains at a constant rate."""

    algorithm = "leaky"

    def __init__(
        self,
        *,
        capacity: int | float,
        drain_rate: int | float,
        clock: Clock | None = None,
        storage: StorageBackend | None = None,
        metrics: MetricsCollector | None = None,
        ttl_seconds: float | None = None,
        max_keys: int | None = None,
    ) -> None:
        self.capacity = float(capacity)
        self.drain_rate = float(drain_rate)
        self._validate_positive("capacity", self.capacity)
        self._validate_positive("drain_rate", self.drain_rate)
        super().__init__(
            clock=clock,
            storage=storage,
            metrics=metrics,
            ttl_seconds=ttl_seconds,
            max_keys=max_keys,
        )

    def try_acquire(self, key: str, cost: int | float = 1) -> Decision:
        cost_value = self._validate_cost(cost)

        def factory(now: float) -> LeakyBucketState:
            return LeakyBucketState(queue_depth=0.0, last_drained=now, last_seen=now)

        def mutate(raw_state: object, now: float) -> tuple[Decision, DecisionMetrics]:
            state = cast(LeakyBucketState, raw_state)
            self._drain_state(state, now)
            state.last_seen = now

            if state.queue_depth + cost_value <= self.capacity:
                state.queue_depth += cost_value
                decision = Decision(
                    allowed=True,
                    remaining=max(0.0, self.capacity - state.queue_depth),
                    retry_after=None,
                    reset_after=self._non_negative(state.queue_depth / self.drain_rate),
                    limit=self.capacity,
                    algorithm=self.algorithm,
                    reason="allowed",
                )
            else:
                # A single request larger than the whole bucket can never be
                # queued, so draining will not make room: no retry_after.
                impossible = cost_value > self.capacity
                overflow = state.queue_depth + cost_value - self.capacity
                decision = Decision(
                    allowed=False,
                    remaining=max(0.0, self.capacity - state.queue_depth),
                    retry_after=None if impossible else self._non_negative(overflow / self.drain_rate),
                    reset_after=self._non_negative(state.queue_depth / self.drain_rate),
                    limit=self.capacity,
                    algorithm=self.algorithm,
                    reason="cost exceeds capacity" if impossible else "queue full",
                )
            return decision, DecisionMetrics(
                current_usage=state.queue_depth,
                queue_depth=state.queue_depth,
            )

        decision, metrics = self.storage.mutate(key, factory, mutate)
        return self._record_decision(key, decision, metrics)

    def drain_once(self, key: str) -> float:
        """Drain one key in place and return its current queue depth.

        Uses ``mutate_existing`` so the autonomous drain worker never recreates
        a key that TTL or LRU eviction has already removed.
        """

        result = self.storage.mutate_existing(key, self._drain_mutator)
        return 0.0 if result is None else result

    def drain_once_all(self) -> dict[str, float]:
        """Drain all currently known leaky bucket states."""

        depths: dict[str, float] = {}
        for key in self.storage.list_keys():
            snapshot = self.storage.get_snapshot(key)
            if snapshot is None or snapshot.state_type != "LeakyBucketState":
                continue
            result = self.storage.mutate_existing(key, self._drain_mutator)
            if result is not None:
                depths[key] = result
        return depths

    def _drain_mutator(self, raw_state: object, now: float) -> float:
        state = cast(LeakyBucketState, raw_state)
        self._drain_state(state, now)
        state.last_seen = now
        return state.queue_depth

    def _drain_state(self, state: LeakyBucketState, now: float) -> None:
        elapsed = max(0.0, now - state.last_drained)
        drained = elapsed * self.drain_rate
        state.queue_depth = max(0.0, state.queue_depth - drained)
        state.last_drained = now

