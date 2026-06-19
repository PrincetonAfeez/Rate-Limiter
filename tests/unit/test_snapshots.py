"""Test snapshots."""

from ratelimiter.observability.snapshots import compact_float, compact_mapping


def test_compact_float_rounds_floats() -> None:
    assert compact_float(1.23456789) == 1.234568
    assert compact_float(42) == 42
    assert compact_float("unchanged") == "unchanged"


def test_compact_mapping_applies_compact_float() -> None:
    assert compact_mapping({"tokens": 3.14159265, "count": 1}) == {
        "tokens": 3.141593,
        "count": 1,
    }
