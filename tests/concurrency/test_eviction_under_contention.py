"""Test eviction under contention."""

import threading
from concurrent.futures import ThreadPoolExecutor

from ratelimiter.algorithms.fixed_window import FixedWindowLimiter
from ratelimiter.concurrency.locks import LockManager
from ratelimiter.storage.memory import InMemoryStorage


def test_concurrent_lru_eviction_does_not_deadlock() -> None:
    """Many threads evicting under a tight LRU cap must not deadlock.

    Eviction acquires a victim's lock stripe; doing so while still holding the
    mutating key's stripe is a lock-ordering hazard that can deadlock two
    concurrent writers. Using only two stripes maximizes collisions so a
    regression surfaces quickly. A watchdog thread bounds the wait so the test
    fails fast instead of hanging if the deadlock returns.
    """

    completed = threading.Event()
    errors: list[BaseException] = []

    def workload() -> None:
        try:
            lock_manager = LockManager(stripes=2)
            storage = InMemoryStorage(lock_manager=lock_manager, max_keys=2)
            limiter = FixedWindowLimiter(limit=1000, window_seconds=60, storage=storage)
            keys = [f"k{index}" for index in range(8)]

            def hammer(worker: int) -> None:
                for i in range(1000):
                    limiter.try_acquire(keys[(worker + i) % len(keys)])

            with ThreadPoolExecutor(max_workers=6) as executor:
                list(executor.map(hammer, range(6)))

            assert len(storage.list_keys()) <= 2
        except BaseException as exc:  # noqa: BLE001 - surface to the main thread
            errors.append(exc)
        finally:
            completed.set()

    runner = threading.Thread(target=workload, daemon=True)
    runner.start()

    assert completed.wait(timeout=30), "concurrent LRU eviction deadlocked"
    assert not errors, f"workload raised: {errors[0]!r}"
