"""Test package exports."""

import ratelimiter
from ratelimiter.core.errors import (
    ConfigError,
    InvalidCostError,
    InvalidLimitError,
    RateLimiterError,
    WorkerLifecycleError,
)


def test_package_version_and_exports() -> None:
    assert ratelimiter.__version__
    for name in ratelimiter.__all__:
        assert hasattr(ratelimiter, name)


def test_exception_hierarchy() -> None:
    assert issubclass(ConfigError, RateLimiterError)
    assert issubclass(InvalidCostError, (RateLimiterError, ValueError))
    assert issubclass(InvalidLimitError, (RateLimiterError, ValueError))
    assert issubclass(WorkerLifecycleError, (RateLimiterError, RuntimeError))
