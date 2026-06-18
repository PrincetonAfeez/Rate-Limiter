"""Test lock striping."""

from ratelimiter.concurrency.locks import LockManager


def test_same_key_maps_to_same_stripe() -> None:
    locks = LockManager(stripes=8)

    assert locks.stripe_index("user") == locks.stripe_index("user")
    assert locks.lock_for("user") is locks.lock_for("user")


def test_lock_manager_has_configured_stripes() -> None:
    locks = LockManager(stripes=16)

    assert locks.stripe_count == 16

