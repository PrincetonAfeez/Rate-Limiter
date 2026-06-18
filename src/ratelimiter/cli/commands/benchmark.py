"""Algorithm comparison benchmark."""

from __future__ import annotations

from ratelimiter.cli.commands.common import run_threaded_traffic
from ratelimiter.factory import build_limiter, require_inspectable
from ratelimiter.observability.logging import get_logger, log_event

_logger = get_logger("ratelimiter.cli.benchmark")


def benchmark(
    *,
    algorithms: list[str],
    keys: int,
    threads: int,
    requests: int,
    limit: float,
    period_seconds: float,
    cost: float = 1.0,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for algorithm in algorithms:
        limiter = build_limiter(
            algorithm,
            limit=limit,
            period_seconds=period_seconds,
            burst=limit * 2 if algorithm in {"token", "leaky", "leaky-bucket"} else None,
            max_keys=keys * 2,
        )
        result = run_threaded_traffic(
            limiter, keys=keys, requests=requests, threads=threads, cost=cost
        )
        internals = require_inspectable(limiter)
        result["algorithm"] = algorithm
        result["approximate_memory_bytes"] = internals.storage.estimate_memory_bytes()
        rows.append(result)

    log_event(
        _logger,
        "benchmark.summary",
        algorithms=algorithms,
        keys=keys,
        threads=threads,
        requests=requests,
        limit=limit,
        period_seconds=period_seconds,
        cost=cost,
        results=[
            {
                "algorithm": row["algorithm"],
                "allowed": row["allowed"],
                "denied": row["denied"],
                "throughput_per_second": row["throughput_per_second"],
                "approximate_memory_bytes": row["approximate_memory_bytes"],
            }
            for row in rows
        ],
    )
    return rows
