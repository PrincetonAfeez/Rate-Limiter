"""Test cost validation."""

import pytest

from ratelimiter.algorithms.fixed_window import FixedWindowLimiter
from ratelimiter.algorithms.leaky_bucket import LeakyBucketLimiter
from ratelimiter.algorithms.sliding_window_counter import SlidingWindowCounterLimiter
from ratelimiter.algorithms.token_bucket import TokenBucketLimiter
from ratelimiter.core.errors import InvalidCostError
from ratelimiter.teaching.unsafe_fixed_window import UnsafeFixedWindowLimiter
from ratelimiter.teaching.unsafe_token_bucket import UnsafeTokenBucketLimiter

SAFE_LIMITERS = [
    TokenBucketLimiter,
    FixedWindowLimiter,
    SlidingWindowCounterLimiter,
    LeakyBucketLimiter,
]


def _make_safe_limiter(limiter_cls: type) -> object:
    if limiter_cls is TokenBucketLimiter:
        return TokenBucketLimiter(capacity=5, refill_rate=1)
    if limiter_cls is FixedWindowLimiter:
        return FixedWindowLimiter(limit=5, window_seconds=60)
    if limiter_cls is SlidingWindowCounterLimiter:
        return SlidingWindowCounterLimiter(limit=5, window_seconds=60)
    return LeakyBucketLimiter(capacity=5, drain_rate=1)


@pytest.mark.parametrize("limiter_cls", SAFE_LIMITERS)
@pytest.mark.parametrize("cost", [0, -1, -0.5])
def test_safe_limiters_reject_non_positive_cost(limiter_cls: type, cost: float) -> None:
    limiter = _make_safe_limiter(limiter_cls)

    with pytest.raises(InvalidCostError, match="cost must be positive"):
        limiter.try_acquire("user", cost=cost)  # type: ignore[union-attr]


@pytest.mark.parametrize("limiter_cls", SAFE_LIMITERS)
@pytest.mark.parametrize("cost", [float("nan"), float("inf"), float("-inf")])
def test_safe_limiters_reject_non_finite_cost(limiter_cls: type, cost: float) -> None:
    limiter = _make_safe_limiter(limiter_cls)

    with pytest.raises(InvalidCostError, match="finite"):
        limiter.try_acquire("user", cost=cost)  # type: ignore[union-attr]


@pytest.mark.parametrize(
    "limiter_factory",
    [
        lambda: UnsafeTokenBucketLimiter(capacity=5, refill_rate=1),
        lambda: UnsafeFixedWindowLimiter(limit=5, window_seconds=60),
    ],
)
@pytest.mark.parametrize("cost", [0, float("nan")])
def test_unsafe_limiters_reject_invalid_cost(limiter_factory, cost: float) -> None:
    limiter = limiter_factory()

    with pytest.raises(InvalidCostError):
        limiter.try_acquire("user", cost=cost)


def test_unsafe_fixed_window_rejects_oversized_cost() -> None:
    limiter = UnsafeFixedWindowLimiter(limit=5, window_seconds=60)

    decision = limiter.try_acquire("user", cost=10)

    assert not decision.allowed
    assert decision.retry_after is None
    assert decision.reason == "cost exceeds limit"


def test_unsafe_token_bucket_rejects_oversized_cost() -> None:
    limiter = UnsafeTokenBucketLimiter(capacity=5, refill_rate=1)

    decision = limiter.try_acquire("user", cost=10)

    assert not decision.allowed
    assert decision.retry_after is None
    assert decision.reason == "cost exceeds capacity"
