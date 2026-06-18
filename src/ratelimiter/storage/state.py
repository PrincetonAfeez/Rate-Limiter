"""Dataclasses stored by the in-memory backend."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TokenBucketState:
    tokens: float
    last_refill: float
    last_seen: float


@dataclass(slots=True)
class FixedWindowState:
    window_start: float
    count: float
    last_seen: float


@dataclass(slots=True)
class SlidingWindowCounterState:
    window_start: float
    current_count: float
    previous_count: float
    last_seen: float


@dataclass(slots=True)
class LeakyBucketState:
    queue_depth: float
    last_drained: float
    last_seen: float


@dataclass(slots=True)
class StorageRecord:
    state: object
    created_at: float
    last_access: float
    expires_at: float | None = None

