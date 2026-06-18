"""Shared CLI helpers."""

from __future__ import annotations

import json
import random
import threading
import time
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from ratelimiter.core.decision import Decision
from ratelimiter.core.interface import RateLimiter


def decision_to_line(label: str, decision: Decision) -> str:
    retry = "none" if decision.retry_after is None else f"{decision.retry_after:.3f}s"
    reset = "none" if decision.reset_after is None else f"{decision.reset_after:.3f}s"
    return (
        f"{label}: allowed={decision.allowed} remaining={decision.remaining:.3f} "
        f"retry_after={retry} reset_after={reset} reason={decision.reason}"
    )


def print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, sort_keys=True, default=str))


def run_threaded_traffic(
    limiter: RateLimiter,
    *,
    keys: int,
    requests: int,
    threads: int,
    hot_key: bool = False,
    cost: float = 1.0,
) -> dict[str, Any]:
    thread_count = max(1, threads)
    request_count = max(0, requests)
    key_names = ["hot"] if hot_key else [f"key-{index}" for index in range(max(1, keys))]
    rng = random.Random(42)
    assignments = [rng.choice(key_names) for _ in range(request_count)]
    barrier = threading.Barrier(thread_count)

    def worker(worker_index: int) -> tuple[int, int]:
        allowed = 0
        denied = 0
        barrier.wait()
        for index in range(worker_index, request_count, thread_count):
            decision = limiter.try_acquire(assignments[index], cost=cost)
            if decision.allowed:
                allowed += 1
            else:
                denied += 1
        return allowed, denied

    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        results = list(executor.map(worker, range(thread_count)))
    elapsed = time.perf_counter() - start
    allowed_total = sum(result[0] for result in results)
    denied_total = sum(result[1] for result in results)
    return {
        "allowed": allowed_total,
        "denied": denied_total,
        "requests": request_count,
        "threads": thread_count,
        "keys": len(key_names),
        "cost": cost,
        "elapsed_seconds": elapsed,
        "throughput_per_second": request_count / elapsed if elapsed > 0 else 0.0,
    }


def emit_lines(lines: Iterable[str]) -> None:
    for line in lines:
        print(line)
