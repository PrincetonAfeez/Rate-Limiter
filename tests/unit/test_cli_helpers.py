"""Test CLI helpers."""

import argparse
import json
import runpy
import sys

import pytest

from ratelimiter.cli.commands.common import decision_to_line, emit_lines, print_json, run_threaded_traffic
from ratelimiter.cli.main import _positive_float, _positive_int, build_parser
from ratelimiter.core.decision import Decision
from ratelimiter.factory import build_limiter


def test_decision_to_line_formats_none_timings() -> None:
    decision = Decision(
        allowed=True,
        remaining=3.5,
        retry_after=None,
        reset_after=None,
        limit=10,
        algorithm="token",
        reason="allowed",
    )
    line = decision_to_line("req", decision)
    assert "retry_after=none" in line
    assert "reset_after=none" in line


def test_run_threaded_traffic_zero_requests() -> None:
    limiter = build_limiter("token", limit=10, period_seconds=1, burst=10)
    result = run_threaded_traffic(limiter, keys=1, requests=0, threads=4)
    assert result["requests"] == 0
    assert result["allowed"] == 0
    assert result["throughput_per_second"] == 0.0


def test_positive_int_and_float_validators() -> None:
    assert _positive_int("3") == 3
    assert _positive_float("2.5") == 2.5
    with pytest.raises(argparse.ArgumentTypeError):
        _positive_int("0")
    with pytest.raises(argparse.ArgumentTypeError):
        _positive_int("x")
    with pytest.raises(argparse.ArgumentTypeError):
        _positive_float("-1")


def test_build_parser_has_all_subcommands() -> None:
    parser = build_parser()
    for command in ("demo", "simulate", "inspect", "reset", "list", "benchmark", "failure-demo"):
        assert command in parser.format_help()


def test_main_module_entrypoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["ratelimit", "--version"])
    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("ratelimiter.cli.main", run_name="__main__")
    assert exc_info.value.code == 0


def test_positive_float_rejects_non_numeric() -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        _positive_float("not-a-number")


def test_emit_lines_and_print_json(capsys) -> None:  # type: ignore[no-untyped-def]
    emit_lines(["line-a", "line-b"])
    out = capsys.readouterr().out
    assert "line-a" in out
    print_json({"ok": True})
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
