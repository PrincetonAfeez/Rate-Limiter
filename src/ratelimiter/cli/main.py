"""argparse command-line entry point."""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from ratelimiter import __version__
from ratelimiter.cli.commands.benchmark import benchmark
from ratelimiter.cli.commands.common import emit_lines, print_json
from ratelimiter.cli.commands.demo import run_demo
from ratelimiter.cli.commands.failure_demo import failure_demo
from ratelimiter.cli.commands.inspect import inspect_key
from ratelimiter.cli.commands.list import list_limiters
from ratelimiter.cli.commands.reset import reset_key
from ratelimiter.cli.commands.simulate import simulate
from ratelimiter.core.errors import RateLimiterError


def _positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if number < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def _positive_float(value: str) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a number") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("must be a positive number")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ratelimit")
    parser.add_argument("--version", action="version", version=f"ratelimit {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo_parser = subparsers.add_parser("demo", help="run scripted demos")
    demo_parser.add_argument(
        "name",
        choices=[
            "all",
            "fixed-window-boundary",
            "token-bucket-burst",
            "sliding-window-counter",
            "leaky-bucket-drain",
            "ttl-sweeper",
            "concurrency-safe",
            "concurrency-unsafe",
        ],
    )

    simulate_parser = subparsers.add_parser("simulate", help="fire synthetic traffic")
    simulate_parser.add_argument("--algorithm", default="token")
    simulate_parser.add_argument("--keys", type=_positive_int, default=100)
    simulate_parser.add_argument("--requests", type=_positive_int, default=10000)
    simulate_parser.add_argument("--threads", type=_positive_int, default=8)
    simulate_parser.add_argument("--limit", type=_positive_float, default=100)
    simulate_parser.add_argument("--period-seconds", type=_positive_float, default=60)
    simulate_parser.add_argument("--burst", type=_positive_float)
    simulate_parser.add_argument("--config", help="load limiter rules from a config file")
    simulate_parser.add_argument("--name", help="limiter name within --config")
    simulate_parser.add_argument(
        "--hot-key",
        action="store_true",
        help="route all requests to a single hot key for contention demos",
    )
    simulate_parser.add_argument(
        "--cost",
        type=_positive_float,
        default=1.0,
        help="capacity consumed by each simulated request",
    )

    inspect_parser = subparsers.add_parser("inspect", help="inspect one key")
    inspect_parser.add_argument("key")
    inspect_parser.add_argument("--algorithm", default="token")
    inspect_parser.add_argument("--limit", type=_positive_float, default=10)
    inspect_parser.add_argument("--period-seconds", type=_positive_float, default=60)
    inspect_parser.add_argument("--config", help="load limiter rules from a config file")
    inspect_parser.add_argument("--name", help="limiter name within --config")

    reset_parser = subparsers.add_parser("reset", help="clear one key")
    reset_parser.add_argument("key")
    reset_parser.add_argument("--algorithm", default="token")
    reset_parser.add_argument("--limit", type=_positive_float, default=10)
    reset_parser.add_argument("--period-seconds", type=_positive_float, default=60)
    reset_parser.add_argument("--config", help="load limiter rules from a config file")
    reset_parser.add_argument("--name", help="limiter name within --config")

    list_parser = subparsers.add_parser("list", help="list configured limiters")
    list_parser.add_argument("--config")

    benchmark_parser = subparsers.add_parser("benchmark", help="compare algorithms")
    benchmark_parser.add_argument("--algorithms", default="token,fixed-window,sliding-window-counter,leaky")
    benchmark_parser.add_argument("--keys", type=_positive_int, default=1000)
    benchmark_parser.add_argument("--threads", type=_positive_int, default=16)
    benchmark_parser.add_argument("--requests", type=_positive_int, default=20000)
    benchmark_parser.add_argument("--limit", type=_positive_float, default=100)
    benchmark_parser.add_argument("--period-seconds", type=_positive_float, default=60)
    benchmark_parser.add_argument(
        "--cost",
        type=_positive_float,
        default=1.0,
        help="capacity consumed by each benchmark request",
    )

    failure_parser = subparsers.add_parser("failure-demo", help="run deliberate failure demos")
    failure_parser.add_argument("name", choices=["race"])

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "demo":
            emit_lines(run_demo(args.name))
        elif args.command == "simulate":
            print_json(
                simulate(
                    algorithm=args.algorithm,
                    keys=args.keys,
                    requests=args.requests,
                    threads=args.threads,
                    limit=args.limit,
                    period_seconds=args.period_seconds,
                    burst=args.burst,
                    config=args.config,
                    name=args.name,
                    hot_key=args.hot_key,
                    cost=args.cost,
                )
            )
        elif args.command == "inspect":
            print_json(
                inspect_key(
                    args.key,
                    algorithm=args.algorithm,
                    limit=args.limit,
                    period_seconds=args.period_seconds,
                    config=args.config,
                    name=args.name,
                )
            )
        elif args.command == "reset":
            print_json(
                reset_key(
                    args.key,
                    algorithm=args.algorithm,
                    limit=args.limit,
                    period_seconds=args.period_seconds,
                    config=args.config,
                    name=args.name,
                )
            )
        elif args.command == "list":
            print_json(list_limiters(args.config))
        elif args.command == "benchmark":
            print_json(
                benchmark(
                    algorithms=[item.strip() for item in args.algorithms.split(",") if item.strip()],
                    keys=args.keys,
                    threads=args.threads,
                    requests=args.requests,
                    limit=args.limit,
                    period_seconds=args.period_seconds,
                    cost=args.cost,
                )
            )
        elif args.command == "failure-demo":
            emit_lines(failure_demo(args.name))
    except (RateLimiterError, ValueError) as exc:
        # Runtime failures are distinct from argparse usage errors: print a
        # clean message (no usage dump) and exit 1, leaving exit 2 to argparse.
        print(f"ratelimit: error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

