"""Test benchmark."""

from ratelimiter.cli.commands.benchmark import benchmark
from ratelimiter.observability.logging import get_logger


def test_benchmark_helper_returns_rows() -> None:
    rows = benchmark(
        algorithms=["token", "fixed-window"],
        keys=5,
        threads=2,
        requests=50,
        limit=10,
        period_seconds=60,
    )

    assert {row["algorithm"] for row in rows} == {"token", "fixed-window"}
    # Each row reports the comparison fields the benchmark exists to surface.
    assert all("approximate_memory_bytes" in row for row in rows)
    assert all("throughput_per_second" in row for row in rows)


def test_benchmark_emits_summary_log(caplog) -> None:  # type: ignore[no-untyped-def]
    caplog.set_level("INFO", logger=get_logger("ratelimiter.cli.benchmark").name)

    benchmark(
        algorithms=["token"],
        keys=2,
        threads=1,
        requests=10,
        limit=5,
        period_seconds=60,
    )

    assert any("benchmark.summary" in record.message for record in caplog.records)

