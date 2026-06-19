"""Test config extended."""

import importlib
from pathlib import Path

import pytest

from ratelimiter.core.config import (
    LimitRule,
    _load_minimal_yaml,
    _load_simple_yaml,
    _rules_from_mapping,
    load_config,
    normalize_algorithm,
    parse_rule,
)
from ratelimiter.core.errors import ConfigError


@pytest.mark.parametrize(
    ("alias", "expected"),
    [
        ("token", "token"),
        ("token-bucket", "token"),
        ("fixed", "fixed-window"),
        ("fixed-window", "fixed-window"),
        ("sliding", "sliding-window-counter"),
        ("sliding-counter", "sliding-window-counter"),
        ("sliding-window-counter", "sliding-window-counter"),
        ("leaky", "leaky"),
        ("leaky-bucket", "leaky"),
    ],
)
def test_normalize_algorithm_aliases(alias: str, expected: str) -> None:
    assert normalize_algorithm(alias) == expected


def test_normalize_algorithm_rejects_unknown() -> None:
    with pytest.raises(ConfigError, match="unknown algorithm"):
        normalize_algorithm("not-real")


def test_limit_rule_properties() -> None:
    rule = parse_rule("60/min burst 120 algorithm token", name="api")
    assert rule.refill_rate == 1.0
    assert rule.capacity == 120.0
    assert rule.raw.startswith("60/min")


def test_rules_from_mapping_accepts_rules_key() -> None:
    rules = _rules_from_mapping(
        {"rules": {"api": "10/sec algorithm token", "login": {"rule": "50/min algorithm fixed-window"}}}
    )
    assert set(rules) == {"api", "login"}


def test_rules_from_mapping_rejects_non_mapping_section() -> None:
    with pytest.raises(ConfigError, match="mapping"):
        _rules_from_mapping({"limiters": "bad"})


def test_rules_from_mapping_rejects_invalid_limiter_value() -> None:
    with pytest.raises(ConfigError, match="must be a rule string"):
        _rules_from_mapping({"limiters": {"api": {"not_rule": "10/sec"}}})


def test_load_minimal_yaml_nested_and_inline_rules() -> None:
    text = """limiters:
  api:
    rule: "10/sec burst 20 algorithm token"
  login: "50/min algorithm sliding-window-counter"
"""
    data = _load_minimal_yaml(text)
    rules = _rules_from_mapping(data)
    assert rules["api"].algorithm == "token"
    assert rules["login"].algorithm == "sliding-window-counter"


def test_load_minimal_yaml_rejects_unsupported_line() -> None:
    with pytest.raises(ConfigError, match="unsupported YAML line"):
        _load_minimal_yaml("limiters:\n  - bad list item\n")


def test_load_minimal_yaml_rejects_invalid_nested_mapping() -> None:
    text = "limiters:\n  api:\n    not-nested: ok\n  broken-line\n"
    with pytest.raises(ConfigError):
        _load_minimal_yaml(text)


def test_load_simple_yaml_without_pyyaml(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_mod = importlib.import_module("ratelimiter.core.config")

    def raise_import(_name: str) -> object:
        raise ImportError

    monkeypatch.setattr(config_mod.importlib, "import_module", raise_import)
    path = tmp_path / "sample.yaml"
    path.write_text(
        'limiters:\n  api:\n    rule: "10/sec algorithm token"\n',
        encoding="utf-8",
    )
    config = load_config(path)
    assert config.rules["api"].algorithm == "token"


def test_load_simple_yaml_empty_document(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    yaml = pytest.importorskip("yaml")
    config_mod = importlib.import_module("ratelimiter.core.config")
    monkeypatch.setattr(config_mod.importlib, "import_module", lambda _name: yaml)
    path = tmp_path / "empty.yaml"
    path.write_text("", encoding="utf-8")
    config = load_config(path)
    assert config.rules == {}


def test_load_simple_yaml_rejects_non_mapping(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    yaml = pytest.importorskip("yaml")
    config_mod = importlib.import_module("ratelimiter.core.config")
    monkeypatch.setattr(config_mod.importlib, "import_module", lambda _name: yaml)
    path = tmp_path / "bad.yaml"
    path.write_text("- list\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="mapping"):
        load_config(path)


def test_load_minimal_yaml_ignores_blank_lines_and_comments() -> None:
    text = """limiters:

  api:
    rule: "10/sec algorithm token"
"""
    data = _load_minimal_yaml(text)
    assert "limiters" in data


def test_load_minimal_yaml_rejects_bad_indent_two_line() -> None:
    with pytest.raises(ConfigError, match="unsupported YAML line"):
        _load_minimal_yaml("limiters:\n  not-a-mapping-line\n")


def test_load_minimal_yaml_rejects_invalid_nested_value() -> None:
    text = "limiters:\n  api:\n    rule: \"10/sec algorithm token\"\n  login: \"50/min algorithm fixed-window\"\n"
    rules = _rules_from_mapping(_load_minimal_yaml(text))
    assert rules["login"].algorithm == "fixed-window"


def test_load_minimal_yaml_rejects_unexpected_indent() -> None:
    with pytest.raises(ConfigError, match="unsupported YAML line"):
        _load_minimal_yaml("  orphan: value\n")


def test_load_config_single_rule_via_rules_key(tmp_path: Path) -> None:
    path = tmp_path / "rules.json"
    path.write_text('{"rules": {"only": "5/sec algorithm token"}}', encoding="utf-8")
    config = load_config(path)
    assert len(config.rules) == 1
    assert config.rules["only"].limit == 5
