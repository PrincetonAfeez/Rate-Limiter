"""Core contracts shared by every limiter implementation."""

from ratelimiter.core.clock import Clock, FakeClock, RealClock
from ratelimiter.core.config import LimitRule, RateLimiterConfig, load_config
from ratelimiter.core.decision import Decision
from ratelimiter.core.errors import ConfigError
from ratelimiter.core.interface import InspectableLimiter, RateLimiter

__all__ = [
    "Clock",
    "ConfigError",
    "Decision",
    "FakeClock",
    "InspectableLimiter",
    "LimitRule",
    "RateLimiter",
    "RateLimiterConfig",
    "RealClock",
    "load_config",
]
