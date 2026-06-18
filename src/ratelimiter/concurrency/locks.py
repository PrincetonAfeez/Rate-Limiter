"""Per-key lock striping."""

from __future__ import annotations

import threading
import zlib

from ratelimiter.core.errors import InvalidLimitError


class LockManager:
    """Map arbitrary keys to a fixed set of re-entrant lock stripes."""

    def __init__(self, stripes: int = 64) -> None:
        if stripes <= 0:
            raise InvalidLimitError("lock stripe count must be positive")
        self._locks = tuple(threading.RLock() for _ in range(stripes))

    @property
    def stripe_count(self) -> int:
        return len(self._locks)

    def stripe_index(self, key: str) -> int:
        checksum = zlib.crc32(key.encode("utf-8"))
        return checksum % len(self._locks)

    def lock_for(self, key: str) -> threading.RLock:
        return self._locks[self.stripe_index(key)]

