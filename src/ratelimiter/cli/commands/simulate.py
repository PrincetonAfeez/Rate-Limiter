"""Synthetic traffic simulation."""

from __future__ import annotations

from ratelimiter.cli.commands.common import run_threaded_traffic
from ratelimiter.factory import build_limiter, build_limiter_from_rule, require_inspectable, rule_from_config


def simulate(
    *,
    algorithm: str,
    keys: int,
    requests: int,
    threads: int,
    limit: float,
    period_seconds: float,
    burst: float | None,
    config: str | None = None,
    name: str | None = None,
    hot_key: bool = False,
    cost: float = 1.0,
) -> dict[str, object]:
    if config is not None:
        rule = rule_from_config(config, name)
        limiter = build_limiter_from_rule(rule, ttl_seconds=rule.period_seconds * 2)
    else:
        limiter = build_limiter(
            algorithm,
            limit=limit,
            period_seconds=period_seconds,
            burst=burst,
            ttl_seconds=period_seconds * 2,
        )
    result = run_threaded_traffic(
        limiter,
        keys=keys,
        requests=requests,
        threads=threads,
        hot_key=hot_key,
        cost=cost,
    )
    internals = require_inspectable(limiter)
    result["metrics"] = internals.metrics.snapshot()["global"]
    result["approximate_memory_bytes"] = internals.storage.estimate_memory_bytes()
    result["active_keys"] = internals.storage.list_keys()
    result["hot_key"] = hot_key
    return result
