"""Compatibility re-exports for unsafe teaching limiters.

Unsafe implementations live in :mod:`ratelimiter.teaching`; this module keeps
the path referenced by the project scope document.
"""

from ratelimiter.teaching.unsafe_fixed_window import UnsafeFixedWindowLimiter
from ratelimiter.teaching.unsafe_token_bucket import UnsafeTokenBucketLimiter

__all__ = ["UnsafeFixedWindowLimiter", "UnsafeTokenBucketLimiter"]
