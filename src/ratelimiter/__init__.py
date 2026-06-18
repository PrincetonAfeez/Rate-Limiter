"""CLI-first rate limiting library for systems-style Python practice."""

from ratelimiter.algorithms.fixed_window import FixedWindowLimiter
from ratelimiter.algorithms.leaky_bucket import LeakyBucketLimiter
from ratelimiter.algorithms.sliding_window_counter import SlidingWindowCounterLimiter
from ratelimiter.algorithms.token_bucket import TokenBucketLimiter
from ratelimiter.core.clock import FakeClock, RealClock
from ratelimiter.core.config import LimitRule, RateLimiterConfig, load_config
from ratelimiter.core.decision import Decision
from ratelimiter.core.errors import ConfigError
from ratelimiter.core.interface import InspectableLimiter, RateLimiter
from ratelimiter.factory import build_limiter, build_limiter_from_rule, require_inspectable, rule_from_config
from ratelimiter.observability.metrics import MetricsCollector
from ratelimiter.storage.memory import InMemoryStorage
from ratelimiter.workers.leaky_drain_worker import LeakyBucketDrainWorker
from ratelimiter.workers.sweeper import SweeperWorker

# Single source of truth for the package version; pyproject.toml reads this
# attribute (dynamic version), and the CLI exposes it via ``--version``.
__version__ = "0.1.7"

__all__ = [
    "ConfigError",
    "Decision",
    "FakeClock",
    "FixedWindowLimiter",
    "InMemoryStorage",
    "InspectableLimiter",
    "LeakyBucketDrainWorker",
    "LeakyBucketLimiter",
    "LimitRule",
    "MetricsCollector",
    "RateLimiter",
    "RateLimiterConfig",
    "RealClock",
    "SlidingWindowCounterLimiter",
    "SweeperWorker",
    "TokenBucketLimiter",
    "__version__",
    "build_limiter",
    "build_limiter_from_rule",
    "load_config",
    "require_inspectable",
    "rule_from_config",
]
