"""Test CLI modules."""

import pytest

from ratelimiter.cli.commands.benchmark import benchmark
from ratelimiter.cli.commands.demo import run_demo
from ratelimiter.cli.commands.inspect import inspect_key
from ratelimiter.cli.commands.list import list_limiters
from ratelimiter.cli.commands.reset import reset_key
from ratelimiter.cli.commands.simulate import simulate


def test_list_limiters_without_config() -> None:
    payload = list_limiters()
    assert "default" in payload["configured_limiters"]
    assert payload["active_keys"] == []
    assert "active_keys_note" in payload


def test_simulate_populates_active_keys_and_metrics() -> None:
    result = simulate(
        algorithm="token",
        keys=2,
        requests=4,
        threads=1,
        limit=10,
        period_seconds=60,
        burst=10,
    )
    assert result["active_keys"] == ["key-0", "key-1"]
    assert result["metrics"]["total_allowed"] + result["metrics"]["total_denied"] == 4


def test_reset_key_on_process_local_limiter() -> None:
    reset = reset_key("key-0", algorithm="token", limit=10, period_seconds=60)
    assert reset["key"] == "key-0"
    assert reset["reset"] is False
    assert reset["active_keys"] == []


def test_inspect_key_reports_inactive_for_unknown_key() -> None:
    inspected = inspect_key("missing", algorithm="token", limit=10, period_seconds=60)
    assert inspected["active"] is False
    assert inspected["state"] is None


def test_benchmark_returns_rows() -> None:
    rows = benchmark(
        algorithms=["token"],
        keys=1,
        threads=1,
        requests=2,
        limit=5,
        period_seconds=60,
        cost=1.0,
    )
    assert rows[0]["algorithm"] == "token"
    assert rows[0]["requests"] == 2


@pytest.mark.parametrize(
    "demo_name",
    [
        "fixed-window-boundary",
        "token-bucket-burst",
        "sliding-window-counter",
        "leaky-bucket-drain",
        "ttl-sweeper",
        "concurrency-safe",
        "concurrency-unsafe",
    ],
)
def test_each_demo_script_runs(demo_name: str) -> None:
    lines = run_demo(demo_name)
    assert lines
    assert demo_name.split("-")[0] in lines[0] or demo_name in lines[0]
