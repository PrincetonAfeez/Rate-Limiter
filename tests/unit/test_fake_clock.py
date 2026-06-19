"""Test fake clock."""

import pytest

from fixtures.fake_clock import FakeClock


def test_fake_clock_advances_deterministically() -> None:
    clock = FakeClock(start=10)

    assert clock.now() == 10
    assert clock.advance(2.5) == 12.5
    clock.sleep(0.5)
    assert clock.now() == 13


def test_fake_clock_never_moves_backwards() -> None:
    clock = FakeClock(start=5)

    with pytest.raises(ValueError):
        clock.advance(-1)

