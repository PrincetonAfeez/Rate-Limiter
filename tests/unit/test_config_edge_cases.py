"""Test config edge cases."""

import pytest

from ratelimiter.core.config import _load_minimal_yaml
from ratelimiter.core.errors import ConfigError


def test_load_minimal_yaml_nested_rule_form() -> None:
    text = """limiters:
  api:
    rule: "10/sec algorithm token"
"""
    data = _load_minimal_yaml(text)
    assert data["limiters"]["api"]["rule"] == "10/sec algorithm token"


def test_load_minimal_yaml_invalid_mapping_on_scalar_limiter() -> None:
    with pytest.raises(ConfigError):
        _load_minimal_yaml("limiters:\n  api: \"10/sec algorithm token\"\n    extra: value\n")
