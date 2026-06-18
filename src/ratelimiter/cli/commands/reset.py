"""Reset one key."""

from __future__ import annotations

from typing import Any

from ratelimiter.factory import build_limiter, build_limiter_from_rule, require_inspectable, rule_from_config


def reset_key(
    key: str,
    *,
    algorithm: str,
    limit: float,
    period_seconds: float,
    config: str | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    """Clear one key's state and report whether anything was actually removed."""

    if config is not None:
        rule = rule_from_config(config, name)
        limiter = build_limiter_from_rule(rule)
    else:
        limiter = build_limiter(algorithm, limit=limit, period_seconds=period_seconds)
    internals = require_inspectable(limiter)
    removed = internals.storage.reset(key)
    return {"key": key, "reset": removed, "active_keys": internals.storage.list_keys()}
