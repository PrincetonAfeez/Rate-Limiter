"""Test teaching."""

from ratelimiter.core.clock import FakeClock
from ratelimiter.teaching.race_explainer import check_then_act_timeline, over_admission_summary
from ratelimiter.teaching.unsafe_fixed_window import UnsafeFixedWindowLimiter
from ratelimiter.teaching.unsafe_token_bucket import UnsafeTokenBucketLimiter


def test_race_explainer_timeline() -> None:
    lines = check_then_act_timeline()
    assert any("Thread A" in line for line in lines)
    assert any("mutate" in line for line in lines)


def test_over_admission_summary() -> None:
    assert over_admission_summary(expected=10, actual=15) == (
        "expected max=10, actual allowed=15, over-admission=5"
    )
    assert over_admission_summary(expected=10, actual=8) == (
        "expected max=10, actual allowed=8, over-admission=0"
    )


def test_unsafe_fixed_window_allow_deny_and_oversized_cost() -> None:
    clock = FakeClock(start=0)
    limiter = UnsafeFixedWindowLimiter(limit=2, window_seconds=10, clock=clock, race_delay=0)
    assert limiter.try_acquire("user").allowed
    assert limiter.try_acquire("user").allowed
    denied = limiter.try_acquire("user")
    assert not denied.allowed
    assert denied.reason == "window limit exceeded"
    oversized = limiter.try_acquire("user", cost=5)
    assert not oversized.allowed
    assert oversized.reason == "cost exceeds limit"


def test_unsafe_token_bucket_allow_deny_refill_and_zero_refill() -> None:
    clock = FakeClock(start=0)
    limiter = UnsafeTokenBucketLimiter(capacity=2, refill_rate=1, clock=clock, race_delay=0)
    assert limiter.try_acquire("user").allowed
    assert limiter.try_acquire("user").allowed
    denied = limiter.try_acquire("user")
    assert not denied.allowed
    assert denied.reason == "not enough tokens"
    clock.advance(1)
    assert limiter.try_acquire("user").allowed

    no_refill = UnsafeTokenBucketLimiter(capacity=1, refill_rate=0, clock=FakeClock(), race_delay=0)
    result = no_refill.try_acquire("user")
    assert result.allowed
    denied_no_refill = no_refill.try_acquire("user")
    assert denied_no_refill.retry_after is None
