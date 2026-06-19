"""Test unsafe reexports."""

from ratelimiter.concurrency.unsafe import UnsafeFixedWindowLimiter, UnsafeTokenBucketLimiter


def test_unsafe_reexports_match_teaching_modules() -> None:
    assert UnsafeFixedWindowLimiter(limit=1, window_seconds=60).algorithm == "unsafe-fixed-window"
    assert UnsafeTokenBucketLimiter(capacity=1, refill_rate=1).algorithm == "unsafe-token"
