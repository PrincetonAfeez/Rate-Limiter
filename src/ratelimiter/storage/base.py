"""Storage backend contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from ratelimiter.concurrency.atomic import StateFactory, StateMutation


@dataclass(frozen=True, slots=True)
class StateSnapshot:
    """Serializable view of one stored key."""

    key: str
    state_type: str
    state: dict[str, Any]
    created_at: float
    last_access: float
    expires_at: float | None


class StorageBackend(ABC):
    """Abstract boundary between algorithms and state persistence."""

    @abstractmethod
    def mutate(
        self,
        key: str,
        factory: StateFactory,
        mutator: StateMutation,
    ) -> Any:
        """Atomically create/read/update a key's state.

        ``factory`` and ``mutator`` both receive the monotonic timestamp read
        *inside* the lock, so every time-based calculation happens within the
        atomic section rather than from a value captured before locking.
        """

    @abstractmethod
    def mutate_existing(self, key: str, mutator: StateMutation) -> Any | None:
        """Atomically update a key only if it already exists.

        Returns ``None`` when the key is absent or expired. Unlike
        :meth:`mutate`, this never creates a key, so background workers cannot
        resurrect state that TTL or LRU eviction has removed.
        """

    @abstractmethod
    def get_snapshot(self, key: str) -> StateSnapshot | None:
        """Return a safe snapshot for one key."""

    @abstractmethod
    def snapshot(self) -> dict[str, StateSnapshot]:
        """Return safe snapshots for every known key."""

    @abstractmethod
    def reset(self, key: str) -> bool:
        """Delete a key if present."""

    @abstractmethod
    def list_keys(self) -> list[str]:
        """List known active keys."""

    @abstractmethod
    def expire(self, now: float | None = None) -> int:
        """Expire idle keys and return the number removed."""

    @abstractmethod
    def estimate_memory_bytes(self) -> int:
        """Return an approximate memory footprint for demo output."""
