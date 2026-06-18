"""Unsafe teaching implementations.

These classes are intentionally excluded from the normal public API.
"""

from ratelimiter.teaching.unsafe_fixed_window import UnsafeFixedWindowLimiter
from ratelimiter.teaching.unsafe_token_bucket import UnsafeTokenBucketLimiter

__all__ = ["UnsafeFixedWindowLimiter", "UnsafeTokenBucketLimiter"]

