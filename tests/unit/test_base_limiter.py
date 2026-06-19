"""Test base limiter."""

import pytest

from ratelimiter.algorithms.base import BaseLimiter, DecisionMetrics
from ratelimiter.algorithms.token_bucket import TokenBucketLimiter
from ratelimiter.core.errors import InvalidLimitError


def test_validate_positive_rejects_non_positive() -> None:
    with pytest.raises(InvalidLimitError, match="capacity must be positive"):
        TokenBucketLimiter(capacity=0, refill_rate=1)


def test_validate_non_negative_rejects_negative_refill() -> None:
    with pytest.raises(InvalidLimitError, match="refill_rate must not be negative"):
        TokenBucketLimiter(capacity=1, refill_rate=-1)


def test_non_negative_clamps_none_and_negative() -> None:
    assert BaseLimiter._non_negative(None) is None
    assert BaseLimiter._non_negative(-3.5) == 0.0
    assert BaseLimiter._non_negative(2.0) == 2.0


def test_decision_metrics_dataclass_fields() -> None:
    metrics = DecisionMetrics(current_usage=3.0, queue_depth=1.5)
    assert metrics.current_usage == 3.0
    assert metrics.queue_depth == 1.5
