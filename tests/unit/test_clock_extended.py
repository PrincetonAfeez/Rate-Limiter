"""Test clock extended."""

import time

import pytest

from ratelimiter.core.clock import FakeClock, RealClock


def test_fake_clock_set_advances_forward() -> None:
    clock = FakeClock(start=1.0)
    clock.set(5.0)
    assert clock.now() == 5.0


def test_fake_clock_set_rejects_backwards_move() -> None:
    clock = FakeClock(start=10.0)
    with pytest.raises(ValueError, match="backwards"):
        clock.set(5.0)


def test_fake_clock_sleep_advances_time() -> None:
    clock = FakeClock(start=0.0)
    clock.sleep(2.5)
    assert clock.now() == 2.5


def test_real_clock_now_and_sleep() -> None:
    clock = RealClock()
    start = clock.now()
    clock.sleep(0.001)
    assert clock.now() >= start
