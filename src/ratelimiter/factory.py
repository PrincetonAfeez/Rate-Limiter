"""Public factory helpers for constructing limiters from rules or CLI flags."""

from __future__ import annotations

from pathlib import Path

from ratelimiter.algorithms.fixed_window import FixedWindowLimiter
from ratelimiter.algorithms.leaky_bucket import LeakyBucketLimiter
from ratelimiter.algorithms.sliding_window_counter import SlidingWindowCounterLimiter
from ratelimiter.algorithms.token_bucket import TokenBucketLimiter
from ratelimiter.core.clock import Clock
from ratelimiter.core.config import LimitRule, load_config, normalize_algorithm
from ratelimiter.core.interface import InspectableLimiter, RateLimiter


def build_limiter(
    algorithm: str,
    *,
    limit: float = 10.0,
    period_seconds: float = 60.0,
    burst: float | None = None,
    clock: Clock | None = None,
    ttl_seconds: float | None = None,
    max_keys: int | None = None,
    refill_rate: float | None = None,
) -> RateLimiter:
    """Build a limiter from explicit flags by parsing a synthetic ``LimitRule``."""

    rule = LimitRule(
        name="cli",
        limit=limit,
        period_seconds=period_seconds,
        algorithm=normalize_algorithm(algorithm),
        burst=burst,
    )
    return build_limiter_from_rule(
        rule,
        clock=clock,
        ttl_seconds=ttl_seconds,
        max_keys=max_keys,
        refill_rate=refill_rate,
    )


def build_limiter_from_rule(
    rule: LimitRule,
    *,
    clock: Clock | None = None,
    ttl_seconds: float | None = None,
    max_keys: int | None = None,
    refill_rate: float | None = None,
) -> RateLimiter:
    """Construct a limiter from a parsed declarative ``LimitRule``."""

    effective_refill = rule.refill_rate if refill_rate is None else refill_rate

    if rule.algorithm == "token":
        return TokenBucketLimiter(
            capacity=rule.capacity,
            refill_rate=effective_refill,
            clock=clock,
            ttl_seconds=ttl_seconds,
            max_keys=max_keys,
        )
    if rule.algorithm == "fixed-window":
        return FixedWindowLimiter(
            limit=rule.limit,
            window_seconds=rule.period_seconds,
            clock=clock,
            ttl_seconds=ttl_seconds,
            max_keys=max_keys,
        )
    if rule.algorithm == "sliding-window-counter":
        return SlidingWindowCounterLimiter(
            limit=rule.limit,
            window_seconds=rule.period_seconds,
            clock=clock,
            ttl_seconds=ttl_seconds,
            max_keys=max_keys,
        )
    if rule.algorithm == "leaky":
        return LeakyBucketLimiter(
            capacity=rule.capacity,
            drain_rate=effective_refill,
            clock=clock,
            ttl_seconds=ttl_seconds,
            max_keys=max_keys,
        )
    raise ValueError(f"unsupported algorithm: {rule.algorithm}")


def require_inspectable(limiter: RateLimiter) -> InspectableLimiter:
    """Return a limiter that exposes storage and metrics for CLI commands."""

    if not isinstance(limiter, InspectableLimiter):
        raise TypeError(f"{type(limiter).__name__} does not expose storage and metrics")
    return limiter


def rule_from_config(config_path: str | Path, name: str | None = None) -> LimitRule:
    """Load a config file and select one named limiter rule."""

    config = load_config(config_path)
    if not config.rules:
        raise ValueError("config defines no limiters")
    if name is None:
        if len(config.rules) == 1:
            return next(iter(config.rules.values()))
        available = ", ".join(sorted(config.rules))
        raise ValueError(f"--name is required; config defines: {available}")
    try:
        return config.rules[name]
    except KeyError:
        available = ", ".join(sorted(config.rules))
        raise ValueError(f"unknown limiter {name!r}; config defines: {available}")
