"""Injectable monotonic clocks."""

from __future__ import annotations

import threading
import time
from typing import Protocol


class Clock(Protocol):
    """Clock interface used by algorithms, storage, and schedulers."""

    def now(self) -> float:
        """Return monotonic seconds."""

    def sleep(self, seconds: float) -> None:
        """Sleep or advance time by the requested duration."""


class RealClock:
    """Clock backed by time.monotonic()."""

    def now(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        time.sleep(max(0.0, seconds))


class FakeClock:
    """Deterministic test clock."""

    def __init__(self, start: float = 0.0) -> None:
        self._now = float(start)
        self._lock = threading.RLock()

    def now(self) -> float:
        with self._lock:
            return self._now

    def advance(self, seconds: float) -> float:
        if seconds < 0:
            raise ValueError("cannot move fake monotonic time backwards")
        with self._lock:
            self._now += float(seconds)
            return self._now

    def set(self, value: float) -> None:
        with self._lock:
            if value < self._now:
                raise ValueError("cannot move fake monotonic time backwards")
            self._now = float(value)

    def sleep(self, seconds: float) -> None:
        self.advance(max(0.0, seconds))

