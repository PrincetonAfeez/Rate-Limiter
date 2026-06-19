"""Test decision extended."""

import logging

import pytest

from ratelimiter.core.decision import Decision


def test_decision_rejects_negative_reset_after() -> None:
    with pytest.raises(ValueError, match="reset_after"):
        Decision(
            allowed=False,
            remaining=0,
            retry_after=None,
            reset_after=-1.0,
            limit=1,
            algorithm="token",
            reason="bad",
        )


def test_decision_clamps_negative_remaining_and_logs(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="ratelimiter.decision"):
        decision = Decision(
            allowed=True,
            remaining=-5.0,
            retry_after=None,
            reset_after=None,
            limit=10,
            algorithm="token",
            reason="test clamp",
        )
    assert decision.remaining == 0.0
    assert "clamped negative remaining" in caplog.text
