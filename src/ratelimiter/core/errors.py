"""Project-specific exceptions."""

from __future__ import annotations


class RateLimiterError(Exception):
    """Base exception for this package."""


class ConfigError(RateLimiterError):
    """Raised when a limiter configuration cannot be parsed."""


class InvalidCostError(RateLimiterError, ValueError):
    """Raised when a request cost is not positive."""


class InvalidLimitError(RateLimiterError, ValueError):
    """Raised when a limiter is configured with impossible values."""


class WorkerLifecycleError(RateLimiterError, RuntimeError):
    """Raised when a background worker cannot satisfy its lifecycle contract."""

