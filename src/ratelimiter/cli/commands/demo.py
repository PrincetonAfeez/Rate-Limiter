"""Scripted capstone demonstrations."""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import cast

from ratelimiter import (
    FakeClock,
    LeakyBucketDrainWorker,
    LeakyBucketLimiter,
    SweeperWorker,
    build_limiter,
    require_inspectable,
)
from ratelimiter.cli.commands.common import decision_to_line, run_threaded_traffic
from ratelimiter.core.interface import RateLimiter
from ratelimiter.teaching.race_explainer import over_admission_summary
from ratelimiter.teaching.unsafe_fixed_window import UnsafeFixedWindowLimiter
from ratelimiter.teaching.unsafe_token_bucket import UnsafeTokenBucketLimiter


def run_demo(name: str) -> list[str]:
    demos = {
        "fixed-window-boundary": demo_fixed_window_boundary,
        "token-bucket-burst": demo_token_bucket_burst,
        "sliding-window-counter": demo_sliding_window_counter,
        "leaky-bucket-drain": demo_leaky_bucket_drain,
        "ttl-sweeper": demo_ttl_sweeper,
        "concurrency-safe": demo_concurrency_safe,
        "concurrency-unsafe": demo_concurrency_unsafe,
    }
    if name == "all":
        lines = ["Rate limiter capstone demo"]
        for demo_name in demos:
            lines.append("")
            lines.extend(demos[demo_name]())
        return lines
    return demos[name]()


def demo_fixed_window_boundary() -> list[str]:
    clock = FakeClock(start=59.9)
    limiter = build_limiter("fixed-window", limit=2, period_seconds=60, clock=clock)
    lines = ["fixed-window-boundary"]
    lines.append(decision_to_line("request 1 at t=59.9", limiter.try_acquire("user")))
    lines.append(decision_to_line("request 2 at t=59.9", limiter.try_acquire("user")))
    clock.advance(0.1)
    lines.append(decision_to_line("request 3 at t=60.0", limiter.try_acquire("user")))
    lines.append(decision_to_line("request 4 at t=60.0", limiter.try_acquire("user")))
    lines.append("boundary burst: four requests fit around a two-request window boundary")
    return lines


def demo_token_bucket_burst() -> list[str]:
    clock = FakeClock()
    limiter = build_limiter("token", limit=1, period_seconds=1, burst=3, clock=clock)
    internals = require_inspectable(limiter)
    lines = ["token-bucket-burst"]
    for index in range(1, 5):
        lines.append(decision_to_line(f"burst request {index}", limiter.try_acquire("user")))
    clock.advance(1.0)
    lines.append(decision_to_line("after one-second refill", limiter.try_acquire("user")))
    internals.storage.estimate_memory_bytes()
    lines.append(str(internals.metrics.snapshot()["global"]))
    return lines


def demo_sliding_window_counter() -> list[str]:
    clock = FakeClock(start=0)
    limiter = build_limiter("sliding-window-counter", limit=4, period_seconds=10, clock=clock)
    lines = ["sliding-window-counter"]
    for index in range(4):
        lines.append(decision_to_line(f"current window request {index + 1}", limiter.try_acquire("user")))
    clock.advance(5)
    lines.append(decision_to_line("half-window weighted request", limiter.try_acquire("user")))
    clock.advance(5)
    lines.append(decision_to_line("new window smoothed request", limiter.try_acquire("user")))
    return lines


def demo_leaky_bucket_drain() -> list[str]:
    limiter = cast(
        LeakyBucketLimiter,
        build_limiter("leaky", limit=50, period_seconds=1, burst=2),
    )
    internals = require_inspectable(limiter)
    lines = ["leaky-bucket-drain"]
    lines.append(decision_to_line("queue request 1", limiter.try_acquire("user")))
    lines.append(decision_to_line("queue request 2", limiter.try_acquire("user")))
    lines.append(decision_to_line("queue request 3", limiter.try_acquire("user")))
    with LeakyBucketDrainWorker(limiter, interval_seconds=0.01):
        time.sleep(0.05)
    lines.append(decision_to_line("after autonomous drain", limiter.try_acquire("user")))
    internals.storage.estimate_memory_bytes()
    lines.append(str(internals.metrics.snapshot()["global"]))
    return lines


def demo_ttl_sweeper() -> list[str]:
    clock = FakeClock()
    limiter = build_limiter("token", limit=1, period_seconds=1, burst=5, clock=clock, ttl_seconds=10)
    internals = require_inspectable(limiter)
    lines = ["ttl-sweeper"]
    limiter.try_acquire("idle-user")
    lines.append(f"active keys before expiry: {internals.storage.list_keys()}")
    clock.advance(11)
    removed = internals.storage.expire()
    lines.append(f"keys removed by expiry sweep: {removed}")
    lines.append(f"active keys after expiry: {internals.storage.list_keys()}")
    worker = SweeperWorker(internals.storage, interval_seconds=1.0, clock=clock, metrics=internals.metrics)
    with worker:
        lines.append(f"sweeper running: {worker.is_running()}")
    lines.append(f"sweeper running after shutdown: {worker.is_running()}")
    lines.append(f"expired_keys metric: {internals.metrics.snapshot()['global']['expired_keys']}")
    return lines


def demo_concurrency_safe() -> list[str]:
    limiter = build_limiter("token", limit=1, period_seconds=1, burst=25, refill_rate=0)
    result = run_threaded_traffic(limiter, keys=1, requests=200, threads=32, hot_key=True)
    lines = ["concurrency-safe"]
    lines.append("expected maximum allowed: 25")
    lines.append(f"actual allowed: {result['allowed']}")
    lines.append(f"denied: {result['denied']}")
    lines.append("safe invariant: actual allowed never exceeds the token capacity")
    return lines


def demo_concurrency_unsafe() -> list[str]:
    expected = 10
    requests, threads = 80, 40

    unsafe_fixed = UnsafeFixedWindowLimiter(limit=expected, window_seconds=60, race_delay=0.003)
    unsafe_fixed_allowed = _hot_key_allowed(unsafe_fixed, requests=requests, threads=threads)

    safe_fixed = build_limiter("fixed-window", limit=expected, period_seconds=60)
    safe_fixed_allowed = _hot_key_allowed(safe_fixed, requests=requests, threads=threads)

    unsafe_token = UnsafeTokenBucketLimiter(capacity=expected, refill_rate=0, race_delay=0.003)
    unsafe_token_allowed = _hot_key_allowed(unsafe_token, requests=requests, threads=threads)

    safe_token = build_limiter("token", limit=1, period_seconds=1, burst=expected, refill_rate=0)
    safe_token_allowed = _hot_key_allowed(safe_token, requests=requests, threads=threads)

    lines = ["concurrency-unsafe"]
    lines.append(f"expected maximum allowed: {expected}")
    lines.append("")
    lines.append("unsafe fixed-window:")
    lines.append(f"  {over_admission_summary(expected=expected, actual=unsafe_fixed_allowed)}")
    lines.append(
        f"  safe fixed-window: {over_admission_summary(expected=expected, actual=safe_fixed_allowed)}"
    )
    lines.append("")
    lines.append("unsafe token-bucket (no refill):")
    lines.append(f"  {over_admission_summary(expected=expected, actual=unsafe_token_allowed)}")
    lines.append(
        f"  safe token-bucket: {over_admission_summary(expected=expected, actual=safe_token_allowed)}"
    )
    lines.append("")
    lines.append("race: unsafe threads read the same counter before another thread writes it")
    lines.append("fix: the safe path does read+update inside one locked mutation, so it never over-admits")
    return lines


def _hot_key_allowed(limiter: RateLimiter, *, requests: int, threads: int) -> int:
    barrier = threading.Barrier(threads)

    def worker(worker_index: int) -> int:
        allowed = 0
        barrier.wait()
        for index in range(worker_index, requests, threads):
            if limiter.try_acquire("hot").allowed:
                allowed += 1
        return allowed

    with ThreadPoolExecutor(max_workers=threads) as executor:
        return sum(executor.map(worker, range(threads)))
