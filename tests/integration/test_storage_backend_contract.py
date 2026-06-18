"""Test storage backend contract."""

from ratelimiter.core.clock import FakeClock
from ratelimiter.storage.memory import InMemoryStorage
from ratelimiter.storage.state import FixedWindowState


def test_storage_mutate_snapshot_and_reset() -> None:
    clock = FakeClock()
    storage = InMemoryStorage(clock=clock)

    def factory(now: float) -> FixedWindowState:
        return FixedWindowState(window_start=0, count=0, last_seen=now)

    storage.mutate("user", factory, lambda state, now: setattr(state, "count", 1))
    snapshot = storage.get_snapshot("user")

    assert snapshot is not None
    assert snapshot.state["count"] == 1
    assert storage.list_keys() == ["user"]
    assert storage.reset("user")
    assert storage.list_keys() == []


def test_storage_ttl_expire() -> None:
    clock = FakeClock()
    storage = InMemoryStorage(clock=clock, ttl_seconds=5)

    storage.mutate("user", lambda now: FixedWindowState(0, 0, 0), lambda state, now: None)
    clock.advance(5)

    assert storage.expire() == 1
    assert storage.list_keys() == []


def test_storage_mutate_existing_never_creates_keys() -> None:
    clock = FakeClock()
    storage = InMemoryStorage(clock=clock)

    # An absent key is left absent: no factory means no resurrection.
    assert storage.mutate_existing("ghost", lambda state, now: 1) is None
    assert storage.list_keys() == []

    # A present key is updated and the mutator result is returned.
    storage.mutate("user", lambda now: FixedWindowState(0, 1, now), lambda state, now: None)
    result = storage.mutate_existing("user", lambda state, now: state.count)
    assert result == 1

