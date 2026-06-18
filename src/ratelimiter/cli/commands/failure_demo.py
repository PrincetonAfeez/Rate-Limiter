"""Failure demonstrations."""

from __future__ import annotations

from ratelimiter.cli.commands.demo import demo_concurrency_unsafe
from ratelimiter.teaching.race_explainer import check_then_act_timeline


def failure_demo(name: str) -> list[str]:
    if name != "race":
        raise ValueError(f"unknown failure demo: {name}")
    return [
        "failure-demo race",
        *check_then_act_timeline(),
        "",
        *demo_concurrency_unsafe()[1:],
    ]
