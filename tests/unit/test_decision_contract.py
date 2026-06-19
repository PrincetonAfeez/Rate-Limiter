"""Test decision contract."""

import pytest

from ratelimiter.core.decision import Decision


def test_decision_serializes() -> None:
    decision = Decision(
        allowed=False,
        remaining=0,
        retry_after=1.5,
        reset_after=2.0,
        limit=10,
        algorithm="token",
        reason="not enough tokens",
    )

    assert decision.to_dict()["retry_after"] == 1.5
    assert decision.to_dict()["reason"] == "not enough tokens"


def test_decision_rejects_negative_retry_after() -> None:
    with pytest.raises(ValueError):
        Decision(
            allowed=False,
            remaining=0,
            retry_after=-0.1,
            reset_after=None,
            limit=1,
            algorithm="token",
            reason="bad",
        )

