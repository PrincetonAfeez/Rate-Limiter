"""Test config parser."""

from pathlib import Path

import pytest

from fixtures.configs import FIXED_RULE, LEAKY_RULE, SLIDING_RULE, TOKEN_RULE

from ratelimiter.core.config import load_config, parse_rule
from ratelimiter.core.errors import ConfigError


def test_parse_fixture_rules_cover_every_algorithm() -> None:
    assert parse_rule(TOKEN_RULE, name="api").algorithm == "token"
    assert parse_rule(FIXED_RULE, name="downloads").algorithm == "fixed-window"
    assert parse_rule(SLIDING_RULE, name="login").algorithm == "sliding-window-counter"
    assert parse_rule(LEAKY_RULE, name="queue").algorithm == "leaky"


def test_parse_rule_with_burst_and_algorithm() -> None:
    rule = parse_rule("10/sec burst 20 algorithm token", name="api")

    assert rule.name == "api"
    assert rule.limit == 10
    assert rule.period_seconds == 1
    assert rule.capacity == 20
    assert rule.algorithm == "token"


def test_load_toml_config() -> None:
    config = load_config(Path("configs/sample_limits.toml"))

    assert config.rules["api"].algorithm == "token"
    assert config.rules["login"].algorithm == "sliding-window-counter"


def test_load_simple_yaml_config() -> None:
    config = load_config(Path("configs/sample_limits.yaml"))

    assert config.rules["queue"].algorithm == "leaky"
    assert config.rules["downloads"].period_seconds == 3600


def test_load_json_config() -> None:
    config = load_config(Path("configs/sample_limits.json"))

    assert config.rules["api"].algorithm == "token"
    assert config.rules["api"].capacity == 20
    assert config.rules["login"].algorithm == "sliding-window-counter"
    assert config.rules["queue"].algorithm == "leaky"


def test_parse_rule_rejects_burst_for_fixed_window() -> None:
    with pytest.raises(ConfigError, match="burst is only supported"):
        parse_rule("10/sec burst 20 algorithm fixed-window")


def test_parse_rule_rejects_burst_for_sliding_window() -> None:
    with pytest.raises(ConfigError, match="burst is only supported"):
        parse_rule("50/min burst 100 algorithm sliding-window-counter")


@pytest.mark.parametrize(
    "bad_rule",
    [
        "",  # empty
        "garbage",  # no rate
        "10",  # missing /unit
        "/sec",  # missing limit
        "10/decade",  # unknown unit
        "10/sec burst",  # burst without a value
        "10/sec algorithm",  # algorithm without a value
        "10/sec algorithm nope",  # unknown algorithm
        "0/sec",  # non-positive limit
        "10/sec burst 0",  # non-positive burst
        "10/sec extra-token",  # unexpected trailing token
    ],
)
def test_parse_rule_rejects_malformed_input(bad_rule: str) -> None:
    with pytest.raises(ConfigError):
        parse_rule(bad_rule)


def test_load_config_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_config(tmp_path / "does_not_exist.toml")


def test_load_config_unsupported_extension(tmp_path: Path) -> None:
    config_file = tmp_path / "limits.ini"
    config_file.write_text("[limiters]\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(config_file)

