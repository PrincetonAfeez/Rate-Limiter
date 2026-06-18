"""Test CLI commands."""

import json

import pytest

from ratelimiter.cli.main import main


def test_cli_demo_command(capsys) -> None:  # type: ignore[no-untyped-def]
    assert main(["demo", "token-bucket-burst"]) == 0

    output = capsys.readouterr().out
    assert "token-bucket-burst" in output
    assert "retry_after" in output


def test_cli_demo_all_smoke(capsys) -> None:  # type: ignore[no-untyped-def]
    assert main(["demo", "all"]) == 0

    output = capsys.readouterr().out
    for section in (
        "fixed-window-boundary",
        "token-bucket-burst",
        "sliding-window-counter",
        "leaky-bucket-drain",
        "ttl-sweeper",
        "concurrency-safe",
        "concurrency-unsafe",
    ):
        assert section in output


def test_cli_demo_ttl_sweeper(capsys) -> None:  # type: ignore[no-untyped-def]
    assert main(["demo", "ttl-sweeper"]) == 0

    output = capsys.readouterr().out
    assert "ttl-sweeper" in output
    assert "expired_keys metric" in output


def test_cli_simulate_reports_active_keys(capsys) -> None:  # type: ignore[no-untyped-def]
    assert (
        main(
            [
                "simulate",
                "--algorithm",
                "token",
                "--limit",
                "10",
                "--keys",
                "3",
                "--requests",
                "5",
                "--threads",
                "1",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["active_keys"] == ["key-0", "key-1", "key-2"]


def test_cli_simulate_cost_flag(capsys) -> None:  # type: ignore[no-untyped-def]
    assert (
        main(
            [
                "simulate",
                "--algorithm",
                "token",
                "--limit",
                "10",
                "--burst",
                "10",
                "--requests",
                "3",
                "--threads",
                "1",
                "--keys",
                "1",
                "--cost",
                "5",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["cost"] == 5.0
    assert payload["allowed"] == 2


def test_cli_list_without_config(capsys) -> None:  # type: ignore[no-untyped-def]
    assert main(["list"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert "default" in payload["configured_limiters"]
    assert payload["active_keys"] == []


def test_cli_reset_after_simulate_populated_key(capsys) -> None:  # type: ignore[no-untyped-def]
    assert (
        main(
            [
                "simulate",
                "--algorithm",
                "token",
                "--keys",
                "1",
                "--requests",
                "1",
                "--threads",
                "1",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert main(["reset", "key-0", "--algorithm", "token"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["key"] == "key-0"


def test_cli_inspect_from_config(capsys) -> None:  # type: ignore[no-untyped-def]
    assert (
        main(
            [
                "inspect",
                "user-123",
                "--config",
                "configs/sample_limits.toml",
                "--name",
                "login",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["key"] == "user-123"
    assert payload["algorithm"] == "sliding-window-counter"
    assert payload["active"] is False
    assert "decision" not in payload


def test_cli_simulate_from_json_config(capsys) -> None:  # type: ignore[no-untyped-def]
    assert (
        main(
            [
                "simulate",
                "--config",
                "configs/sample_limits.json",
                "--name",
                "api",
                "--keys",
                "2",
                "--requests",
                "10",
                "--threads",
                "1",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["requests"] == 10
    assert payload["allowed"] + payload["denied"] == 10


def test_cli_list_with_yaml_config(capsys) -> None:  # type: ignore[no-untyped-def]
    assert main(["list", "--config", "configs/sample_limits.yaml"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert "api" in payload["configured_limiters"]
    assert "login" in payload["configured_limiters"]
    assert payload["active_keys"] == []
    assert "active_keys_note" in payload


def test_cli_inspect_is_read_only(capsys) -> None:  # type: ignore[no-untyped-def]
    assert main(["inspect", "user"]) == 0

    output = capsys.readouterr().out
    payload = json.loads(output)
    assert payload["key"] == "user"
    # Inspection must not consume capacity. A fresh, process-local limiter has
    # no state for the key, so it is reported inactive with no decision field.
    assert payload["active"] is False
    assert payload["state"] is None
    assert "decision" not in payload
    assert "last_retry_after" in payload
    assert "last_reset_after" in payload


def test_cli_simulate_hot_key_flag(capsys) -> None:  # type: ignore[no-untyped-def]
    assert (
        main(
            [
                "simulate",
                "--algorithm",
                "token",
                "--limit",
                "5",
                "--requests",
                "20",
                "--threads",
                "4",
                "--hot-key",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["hot_key"] is True
    assert payload["keys"] == 1


def test_cli_demo_concurrency_unsafe(capsys) -> None:  # type: ignore[no-untyped-def]
    assert main(["demo", "concurrency-unsafe"]) == 0

    output = capsys.readouterr().out
    assert "concurrency-unsafe" in output
    assert "over-admission=" in output


def test_cli_failure_demo_race(capsys) -> None:  # type: ignore[no-untyped-def]
    assert main(["failure-demo", "race"]) == 0

    output = capsys.readouterr().out
    assert "failure-demo race" in output
    assert "over-admission=" in output
    assert "check-then-act" in output.lower() or "race" in output.lower()


def test_cli_benchmark_cost_flag(capsys) -> None:  # type: ignore[no-untyped-def]
    assert (
        main(
            [
                "benchmark",
                "--algorithms",
                "token",
                "--keys",
                "1",
                "--threads",
                "1",
                "--requests",
                "4",
                "--limit",
                "5",
                "--cost",
                "5",
            ]
        )
        == 0
    )
    rows = json.loads(capsys.readouterr().out)
    assert len(rows) == 1
    assert rows[0]["cost"] == 5.0
    assert rows[0]["allowed"] == 2


def test_cli_benchmark_accepts_algorithm_aliases(capsys) -> None:  # type: ignore[no-untyped-def]
    assert (
        main(
            [
                "benchmark",
                "--algorithms",
                "token,fixed,sliding",
                "--keys",
                "2",
                "--threads",
                "1",
                "--requests",
                "10",
            ]
        )
        == 0
    )
    rows = json.loads(capsys.readouterr().out)
    assert {row["algorithm"] for row in rows} == {"token", "fixed", "sliding"}


def test_cli_reset_from_config(capsys) -> None:  # type: ignore[no-untyped-def]
    assert (
        main(
            [
                "simulate",
                "--config",
                "configs/sample_limits.toml",
                "--name",
                "api",
                "--keys",
                "1",
                "--requests",
                "1",
                "--threads",
                "1",
            ]
        )
        == 0
    )
    capsys.readouterr()

    # Reset on a fresh limiter still reports False, but accepts --config/--name.
    assert (
        main(
            [
                "reset",
                "key-0",
                "--config",
                "configs/sample_limits.toml",
                "--name",
                "api",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["key"] == "key-0"
    assert "reset" in payload


def test_cli_list_with_config(capsys) -> None:  # type: ignore[no-untyped-def]
    assert main(["list", "--config", "configs/sample_limits.toml"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert "api" in payload["configured_limiters"]


def test_cli_simulate_from_config_drives_a_limiter(capsys) -> None:  # type: ignore[no-untyped-def]
    code = main(
        [
            "simulate",
            "--config",
            "configs/sample_limits.toml",
            "--name",
            "api",
            "--keys",
            "5",
            "--requests",
            "50",
            "--threads",
            "2",
        ]
    )
    assert code == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["requests"] == 50
    assert payload["allowed"] + payload["denied"] == 50


def test_cli_rejects_non_positive_period(capsys) -> None:  # type: ignore[no-untyped-def]
    # Usage error: argparse rejects the value and exits 2.
    with pytest.raises(SystemExit) as exc_info:
        main(["simulate", "--period-seconds", "0"])
    assert exc_info.value.code == 2


def test_cli_runtime_error_exits_1_without_usage(capsys) -> None:  # type: ignore[no-untyped-def]
    code = main(["simulate", "--config", "configs/sample_limits.toml", "--name", "no-such-limiter"])

    assert code == 1
    captured = capsys.readouterr()
    assert "no-such-limiter" in captured.err
    assert "usage:" not in captured.err.lower()


def test_cli_unknown_algorithm_exits_1(capsys) -> None:  # type: ignore[no-untyped-def]
    code = main(["simulate", "--algorithm", "bad-alg"])
    captured = capsys.readouterr()
    assert code == 1
    assert "bad-alg" in captured.err or "unknown algorithm" in captured.err


def test_cli_version(capsys) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])

    assert exc_info.value.code == 0
    assert "ratelimit" in capsys.readouterr().out

