"""Inspect one key (read-only)."""

from __future__ import annotations

from typing import Any

from ratelimiter.core.config import normalize_algorithm
from ratelimiter.factory import build_limiter, build_limiter_from_rule, require_inspectable, rule_from_config
from ratelimiter.observability.snapshots import compact_mapping


def inspect_key(
    key: str,
    *,
    algorithm: str,
    limit: float,
    period_seconds: float,
    config: str | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    """Report a key's stored state without mutating it."""

    if config is not None:
        rule = rule_from_config(config, name)
        limiter = build_limiter_from_rule(rule)
        resolved_algorithm = rule.algorithm
    else:
        limiter = build_limiter(algorithm, limit=limit, period_seconds=period_seconds)
        resolved_algorithm = normalize_algorithm(algorithm)
    internals = require_inspectable(limiter)
    snapshot = internals.storage.get_snapshot(key)
    metrics = compact_mapping(internals.metrics.snapshot()["keys"].get(key, {}))
    return {
        "algorithm": resolved_algorithm,
        "key": key,
        "active": snapshot is not None,
        "state": None if snapshot is None else snapshot.state,
        "metrics": metrics,
        "last_retry_after": metrics.get("last_retry_after"),
        "last_reset_after": metrics.get("last_reset_after"),
    }
