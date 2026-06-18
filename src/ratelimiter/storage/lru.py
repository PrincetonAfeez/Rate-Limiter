"""LRU accounting helpers."""

from __future__ import annotations

from collections.abc import Iterable

from ratelimiter.storage.state import StorageRecord


def least_recently_used(records: dict[str, StorageRecord], exclude: Iterable[str] = ()) -> str | None:
    excluded = set(exclude)
    candidates = ((key, record.last_access) for key, record in records.items() if key not in excluded)
    winner = min(candidates, key=lambda item: item[1], default=None)
    return winner[0] if winner is not None else None

