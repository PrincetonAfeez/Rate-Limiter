"""Standalone algorithm benchmark (separated from the correctness suite).

This is intentionally NOT a pytest test: benchmark results are for comparison,
never a correctness proof, so the suite must not depend on them. The behaviour
of the benchmark helper is covered by tests/integration/test_benchmark.py.

Run it directly:

    python -m pip install -e .
    python tests/benchmarks/benchmark_algorithms.py

or without installing:

    python tests/benchmarks/benchmark_algorithms.py   # bootstraps ../../src onto sys.path
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running from a fresh checkout without installing the package.
_SRC = Path(__file__).resolve().parents[2] / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ratelimiter.cli.commands.benchmark import benchmark  # noqa: E402


def main() -> None:
    rows = benchmark(
        algorithms=["token", "fixed-window", "sliding-window-counter", "leaky"],
        keys=200,
        threads=8,
        requests=5000,
        limit=100,
        period_seconds=60,
    )
    print(json.dumps(rows, indent=2, default=str))


if __name__ == "__main__":
    main()
