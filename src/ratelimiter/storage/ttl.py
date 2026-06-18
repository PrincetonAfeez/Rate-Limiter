"""TTL helpers."""

from __future__ import annotations


def expires_at(now: float, ttl_seconds: float | None) -> float | None:
    if ttl_seconds is None:
        return None
    return now + max(0.0, ttl_seconds)


def is_expired(now: float, deadline: float | None) -> bool:
    return deadline is not None and now >= deadline

