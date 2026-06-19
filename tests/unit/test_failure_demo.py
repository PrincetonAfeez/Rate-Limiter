"""Test failure demo."""

import pytest

from ratelimiter.cli.commands.failure_demo import failure_demo


def test_failure_demo_race_includes_timeline() -> None:
    lines = failure_demo("race")
    assert lines[0] == "failure-demo race"
    assert any("check-then-act" in line for line in lines)


def test_failure_demo_rejects_unknown_name() -> None:
    with pytest.raises(ValueError, match="unknown failure demo"):
        failure_demo("no-such-demo")
