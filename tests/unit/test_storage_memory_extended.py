"""Test storage memory extended."""

import pytest

from ratelimiter.concurrency.locks import LockManager
from ratelimiter.core.clock import FakeClock
from ratelimiter.core.decision import Decision
from ratelimiter.core.errors import InvalidLimitError
from ratelimiter.observability.metrics import MetricsCollector
from ratelimiter.storage.memory import InMemoryStorage, _snapshot_from_state
from ratelimiter.storage.state import FixedWindowState


def test_lock_manager_stripe_index_and_lock_for() -> None:
    manager = LockManager(stripes=8)
    assert manager.stripe_count == 8
    assert manager.stripe_index("user-a") == manager.stripe_index("user-a")
    lock = manager.lock_for("user-a")
    assert lock.acquire(blocking=False)
    lock.release()


def test_lock_manager_rejects_non_positive_stripes() -> None:
    with pytest.raises(InvalidLimitError, match="stripe count"):
        LockManager(stripes=0)


def test_storage_rejects_invalid_ttl_and_max_keys() -> None:
    with pytest.raises(InvalidLimitError, match="ttl_seconds"):
        InMemoryStorage(ttl_seconds=0)
    with pytest.raises(InvalidLimitError, match="max_keys"):
        InMemoryStorage(max_keys=-1)


def test_storage_snapshot_all_keys() -> None:
    clock = FakeClock()
    storage = InMemoryStorage(clock=clock)

    def factory(now: float) -> FixedWindowState:
        return FixedWindowState(window_start=0, count=1, last_seen=now)

    storage.mutate("a", factory, lambda state, now: None)
    storage.mutate("b", factory, lambda state, now: None)
    snapshots = storage.snapshot()
    assert set(snapshots) == {"a", "b"}


def test_storage_expire_records_metrics_and_logs() -> None:
    clock = FakeClock()
    metrics = MetricsCollector(clock)
    storage = InMemoryStorage(clock=clock, ttl_seconds=5, metrics=metrics)
    storage.mutate("user", lambda now: FixedWindowState(0, 0, now), lambda state, now: None)
    clock.advance(6)
    assert storage.expire() == 1
    assert metrics.snapshot()["global"]["expired_keys"] == 1


def test_storage_mutate_refreshes_expired_key() -> None:
    clock = FakeClock()
    metrics = MetricsCollector(clock)
    storage = InMemoryStorage(clock=clock, ttl_seconds=5, metrics=metrics)
    storage.mutate("user", lambda now: FixedWindowState(0, 1, now), lambda state, now: None)
    metrics.record_decision(
        "user",
        Decision(
            allowed=True,
            remaining=0,
            retry_after=None,
            reset_after=None,
            limit=1,
            algorithm="fixed-window",
            reason="seed",
        ),
        current_usage=1,
    )
    clock.advance(6)
    storage.mutate("user", lambda now: FixedWindowState(0, 0, now), lambda state, now: setattr(state, "count", 2))
    assert storage.get_snapshot("user") is not None
    assert storage.get_snapshot("user").state["count"] == 2  # type: ignore[union-attr]


def test_storage_eviction_updates_metrics() -> None:
    clock = FakeClock()
    metrics = MetricsCollector(clock)
    storage = InMemoryStorage(clock=clock, max_keys=1, metrics=metrics)

    def factory(now: float) -> FixedWindowState:
        return FixedWindowState(window_start=0, count=0, last_seen=now)

    storage.mutate("first", factory, lambda state, now: None)
    clock.advance(1)
    storage.mutate("second", factory, lambda state, now: None)
    assert storage.list_keys() == ["second"]
    assert metrics.snapshot()["global"]["evicted_keys"] == 1


def test_snapshot_from_state_supports_non_dataclass() -> None:
    class PlainState:
        def __init__(self) -> None:
            self.value = 7

    snapshot = _snapshot_from_state("k", PlainState(), 1.0, 2.0, 3.0)
    assert snapshot.state_type == "PlainState"
    assert snapshot.state["value"] == 7


def test_snapshot_from_state_supports_non_object_value() -> None:
    snapshot = _snapshot_from_state("k", 42, 1.0, 2.0, None)
    assert snapshot.state == {"value": "42"}


def test_storage_evict_lru_handles_no_eligible_victim(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = FakeClock()
    storage = InMemoryStorage(clock=clock, max_keys=1)

    def factory(now: float) -> FixedWindowState:
        return FixedWindowState(window_start=0, count=0, last_seen=now)

    storage.mutate("a", factory, lambda state, now: None)
    storage.mutate("b", factory, lambda state, now: None)
    assert len(storage.list_keys()) == 1

    import ratelimiter.storage.memory as memory_mod

    original_lru = memory_mod.least_recently_used

    def no_victim(records, exclude=()):  # type: ignore[no-untyped-def]
        if len(records) > 1:
            return None
        return original_lru(records, exclude=exclude)

    monkeypatch.setattr(memory_mod, "least_recently_used", no_victim)
    storage.mutate("c", factory, lambda state, now: None)
    assert len(storage.list_keys()) <= 2


def test_lru_helper_returns_none_for_empty_records() -> None:
    from ratelimiter.storage.lru import least_recently_used

    assert least_recently_used({}) is None
