"""Thread-safe in-memory storage backend."""

from __future__ import annotations

import sys
import threading
from collections.abc import Iterable
from dataclasses import asdict, is_dataclass
from typing import Any, cast

from ratelimiter.concurrency.atomic import StateFactory, StateMutation
from ratelimiter.concurrency.locks import LockManager
from ratelimiter.core.clock import Clock, RealClock
from ratelimiter.core.errors import InvalidLimitError
from ratelimiter.observability.logging import get_logger, log_event
from ratelimiter.observability.metrics import MetricsCollector
from ratelimiter.storage.base import StateSnapshot, StorageBackend
from ratelimiter.storage.lru import least_recently_used
from ratelimiter.storage.state import StorageRecord
from ratelimiter.storage.ttl import expires_at, is_expired


class InMemoryStorage(StorageBackend):
    """Default storage backend with TTL, LRU eviction, and lock striping."""

    def __init__(
        self,
        *,
        clock: Clock | None = None,
        lock_manager: LockManager | None = None,
        ttl_seconds: float | None = None,
        max_keys: int | None = None,
        metrics: MetricsCollector | None = None,
    ) -> None:
        if ttl_seconds is not None and ttl_seconds <= 0:
            raise InvalidLimitError("ttl_seconds must be positive")
        if max_keys is not None and max_keys <= 0:
            raise InvalidLimitError("max_keys must be positive")
        self.clock = clock or RealClock()
        self.lock_manager = lock_manager or LockManager()
        self.ttl_seconds = ttl_seconds
        self.max_keys = max_keys
        self.metrics = metrics
        self._records: dict[str, StorageRecord] = {}
        self._meta_lock = threading.RLock()
        self._logger = get_logger("ratelimiter.storage")

    def mutate(
        self,
        key: str,
        factory: StateFactory,
        mutator: StateMutation,
    ) -> Any:
        stripe = self.lock_manager.lock_for(key)
        with stripe:
            # Read the clock inside the lock so the timestamp used for every
            # time-based calculation is part of the atomic read/modify/write.
            now = self.clock.now()
            record = self._record_for_mutation(key, factory, now)
            result = mutator(record.state, now)
            with self._meta_lock:
                live_record = self._records.get(key)
                if live_record is record:
                    live_record.last_access = now
                    live_record.expires_at = expires_at(now, self.ttl_seconds)
        # Evict *after* releasing this key's stripe. Holding one stripe while
        # acquiring another (the eviction victim's) is a lock-ordering hazard:
        # two concurrent mutations could each wait on the other's stripe and
        # deadlock. The current key is already committed, so eviction of other
        # keys does not need its lock.
        self._evict_lru(exclude_key=key)
        return result

    def mutate_existing(self, key: str, mutator: StateMutation) -> Any | None:
        stripe = self.lock_manager.lock_for(key)
        with stripe:
            now = self.clock.now()
            with self._meta_lock:
                record = self._records.get(key)
                if record is None or is_expired(now, record.expires_at):
                    return None
            # The stripe lock is held, so the record cannot be deleted (reset,
            # expiry, and eviction all acquire the same stripe before removal).
            result = mutator(record.state, now)
            with self._meta_lock:
                live_record = self._records.get(key)
                if live_record is record:
                    live_record.last_access = now
                    live_record.expires_at = expires_at(now, self.ttl_seconds)
            return result

    def get_snapshot(self, key: str) -> StateSnapshot | None:
        stripe = self.lock_manager.lock_for(key)
        with stripe:
            with self._meta_lock:
                record = self._records.get(key)
                # Treat an expired-but-unswept record as absent, matching
                # list_keys and mutate_existing, so reads stay consistent in
                # the window before the sweeper runs.
                if record is None or is_expired(self.clock.now(), record.expires_at):
                    return None
                state = record.state
                created_at = record.created_at
                last_access = record.last_access
                expires_at_value = record.expires_at
            # `state` is owned by this key's stripe (held above), so serializing
            # it outside the global meta lock cannot race a mutator and avoids
            # blocking metadata operations on unrelated keys.
            return _snapshot_from_state(key, state, created_at, last_access, expires_at_value)

    def snapshot(self) -> dict[str, StateSnapshot]:
        with self._meta_lock:
            keys = list(self._records)
        snapshots: dict[str, StateSnapshot] = {}
        for key in keys:
            snapshot = self.get_snapshot(key)
            if snapshot is not None:
                snapshots[key] = snapshot
        return snapshots

    def reset(self, key: str) -> bool:
        stripe = self.lock_manager.lock_for(key)
        with stripe:
            with self._meta_lock:
                removed = self._records.pop(key, None) is not None
        if removed:
            self._forget_metrics((key,))
        return removed

    def list_keys(self) -> list[str]:
        now = self.clock.now()
        with self._meta_lock:
            return sorted(
                key for key, record in self._records.items() if not is_expired(now, record.expires_at)
            )

    def expire(self, now: float | None = None) -> int:
        deadline = self.clock.now() if now is None else now
        with self._meta_lock:
            candidates = [
                key for key, record in self._records.items() if is_expired(deadline, record.expires_at)
            ]

        removed_keys: list[str] = []
        for key in candidates:
            stripe = self.lock_manager.lock_for(key)
            with stripe:
                with self._meta_lock:
                    record = self._records.get(key)
                    if record is not None and is_expired(deadline, record.expires_at):
                        del self._records[key]
                        removed_keys.append(key)

        if removed_keys:
            self._forget_metrics(removed_keys)
            if self.metrics is not None:
                self.metrics.record_expired(len(removed_keys))
            log_event(self._logger, "storage.expired", count=len(removed_keys))
        return len(removed_keys)

    def estimate_memory_bytes(self) -> int:
        with self._meta_lock:
            total = sys.getsizeof(self._records)
            for key, record in self._records.items():
                total += sys.getsizeof(key)
                total += sys.getsizeof(record)
                total += sys.getsizeof(record.state)
        if self.metrics is not None:
            self.metrics.set_memory_estimate(total)
        return total

    def _record_for_mutation(
        self, key: str, factory: StateFactory, now: float
    ) -> StorageRecord:
        with self._meta_lock:
            record = self._records.get(key)
            if record is not None and is_expired(now, record.expires_at):
                del self._records[key]
                record = None
                self._forget_metrics((key,))
                if self.metrics is not None:
                    self.metrics.record_expired()
            if record is None:
                record = StorageRecord(
                    state=factory(now),
                    created_at=now,
                    last_access=now,
                    expires_at=expires_at(now, self.ttl_seconds),
                )
                self._records[key] = record
            else:
                record.last_access = now
                record.expires_at = expires_at(now, self.ttl_seconds)
            return record

    def _evict_lru(self, *, exclude_key: str | None = None) -> None:
        if self.max_keys is None:
            return

        evicted_keys: list[str] = []
        while True:
            with self._meta_lock:
                if len(self._records) <= self.max_keys:
                    break
                exclude = {exclude_key} if exclude_key is not None else set()
                victim = least_recently_used(self._records, exclude=exclude)
                if victim is None:
                    break

            stripe = self.lock_manager.lock_for(victim)
            with stripe:
                with self._meta_lock:
                    if len(self._records) <= self.max_keys:
                        break
                    current_victim = least_recently_used(
                        self._records,
                        exclude={exclude_key} if exclude_key is not None else set(),
                    )
                    if current_victim == victim:
                        del self._records[victim]
                        evicted_keys.append(victim)

        if evicted_keys:
            self._forget_metrics(evicted_keys)
            if self.metrics is not None:
                self.metrics.record_evicted(len(evicted_keys))
            log_event(self._logger, "storage.lru_evicted", count=len(evicted_keys))

    def _forget_metrics(self, keys: Iterable[str]) -> None:
        """Drop per-key metrics for removed keys so metrics stay bounded."""

        if self.metrics is not None:
            self.metrics.forget_many(keys)


def _snapshot_from_state(
    key: str,
    state: object,
    created_at: float,
    last_access: float,
    expires_at_value: float | None,
) -> StateSnapshot:
    if is_dataclass(state) and not isinstance(state, type):
        state_mapping: dict[str, Any] = asdict(cast(Any, state))
    elif hasattr(state, "__dict__"):
        state_mapping = dict(vars(state))
    else:
        state_mapping = {"value": repr(state)}
    return StateSnapshot(
        key=key,
        state_type=type(state).__name__,
        state=state_mapping,
        created_at=created_at,
        last_access=last_access,
        expires_at=expires_at_value,
    )
