"""List configured limiters and active keys."""

from __future__ import annotations

from typing import Any

from ratelimiter.core.config import load_config, parse_rule


def list_limiters(config_path: str | None = None) -> dict[str, Any]:
    if config_path is None:
        rules = {
            "default": parse_rule("10/sec burst 20 algorithm token", name="default"),
            "fixed-demo": parse_rule("50/min algorithm fixed-window", name="fixed-demo"),
            "sliding-demo": parse_rule("50/min algorithm sliding-window-counter", name="sliding-demo"),
            "leaky-demo": parse_rule("20/sec burst 40 algorithm leaky", name="leaky-demo"),
        }
    else:
        rules = load_config(config_path).rules
    return {
        "configured_limiters": {
            name: {
                "algorithm": rule.algorithm,
                "limit": rule.limit,
                "period_seconds": rule.period_seconds,
                "burst": rule.burst,
            }
            for name, rule in rules.items()
        },
        # The default in-memory backend is process-local, so a fresh CLI
        # invocation has no live limiter and therefore no active keys. A shared
        # backend (e.g. Redis) would let this list real keys across processes.
        "active_keys": [],
        "active_keys_note": (
            "in-memory state is process-local; no keys persist across CLI invocations. "
            "Run `ratelimit simulate ...` to see active_keys from that run, or use the "
            "library API and call storage.list_keys() on the same limiter instance."
        ),
    }

