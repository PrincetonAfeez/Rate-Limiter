"""Declarative limiter config parsing."""

from __future__ import annotations

import importlib
import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ratelimiter.core.errors import ConfigError

_RATE_RE = re.compile(r"^\s*(?P<limit>\d+(?:\.\d+)?)\s*/\s*(?P<unit>[A-Za-z]+)\s*")

_UNIT_SECONDS = {
    "s": 1.0,
    "sec": 1.0,
    "second": 1.0,
    "seconds": 1.0,
    "m": 60.0,
    "min": 60.0,
    "minute": 60.0,
    "minutes": 60.0,
    "h": 3600.0,
    "hr": 3600.0,
    "hour": 3600.0,
    "hours": 3600.0,
}

_BURST_ALGORITHMS = frozenset({"token", "leaky"})

_ALGORITHM_ALIASES = {
    "token": "token",
    "token-bucket": "token",
    "fixed": "fixed-window",
    "fixed-window": "fixed-window",
    "sliding": "sliding-window-counter",
    "sliding-counter": "sliding-window-counter",
    "sliding-window-counter": "sliding-window-counter",
    "leaky": "leaky",
    "leaky-bucket": "leaky",
}


@dataclass(frozen=True, slots=True)
class LimitRule:
    """Parsed limiter rule such as ``10/sec burst 20 algorithm token``."""

    name: str
    limit: float
    period_seconds: float
    algorithm: str = "token"
    burst: float | None = None
    raw: str = ""

    @property
    def refill_rate(self) -> float:
        return self.limit / self.period_seconds

    @property
    def capacity(self) -> float:
        return self.burst if self.burst is not None else self.limit


@dataclass(frozen=True, slots=True)
class RateLimiterConfig:
    """Collection of named limiter rules."""

    rules: dict[str, LimitRule]


def normalize_algorithm(name: str) -> str:
    normalized = _ALGORITHM_ALIASES.get(name.strip().lower())
    if normalized is None:
        raise ConfigError(f"unknown algorithm: {name}")
    return normalized


def parse_rule(rule: str, *, name: str = "default") -> LimitRule:
    match = _RATE_RE.match(rule)
    if not match:
        raise ConfigError(f"could not parse rate rule: {rule!r}")

    limit = float(match.group("limit"))
    unit = match.group("unit").lower()
    try:
        period_seconds = _UNIT_SECONDS[unit]
    except KeyError as exc:
        raise ConfigError(f"unknown rate unit: {unit}") from exc

    algorithm = "token"
    burst: float | None = None
    rest = rule[match.end() :].strip()
    tokens = rest.split()
    index = 0
    while index < len(tokens):
        token = tokens[index].lower()
        if token == "burst":
            index += 1
            if index >= len(tokens):
                raise ConfigError("burst requires a value")
            burst = float(tokens[index])
        elif token == "algorithm":
            index += 1
            if index >= len(tokens):
                raise ConfigError("algorithm requires a value")
            algorithm = normalize_algorithm(tokens[index])
        else:
            raise ConfigError(f"unexpected token in rate rule: {tokens[index]}")
        index += 1

    if limit <= 0:
        raise ConfigError("limit must be positive")
    if burst is not None and burst <= 0:
        raise ConfigError("burst must be positive")
    if burst is not None and algorithm not in _BURST_ALGORITHMS:
        raise ConfigError(
            f"burst is only supported for token and leaky algorithms, not {algorithm!r}"
        )

    return LimitRule(
        name=name,
        limit=limit,
        period_seconds=period_seconds,
        algorithm=algorithm,
        burst=burst,
        raw=rule,
    )


def load_config(path: str | Path) -> RateLimiterConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigError(f"config file not found: {config_path}")

    suffix = config_path.suffix.lower()
    if suffix == ".toml":
        data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    elif suffix == ".json":
        data = json.loads(config_path.read_text(encoding="utf-8"))
    elif suffix in {".yaml", ".yml"}:
        data = _load_simple_yaml(config_path.read_text(encoding="utf-8"))
    else:
        raise ConfigError("config must be TOML, JSON, YAML, or YML")

    return RateLimiterConfig(rules=_rules_from_mapping(data))


def _rules_from_mapping(data: dict[str, Any]) -> dict[str, LimitRule]:
    raw_rules = data.get("limiters", data.get("rules", {}))
    if not isinstance(raw_rules, dict):
        raise ConfigError("config must contain a [limiters] mapping")

    parsed: dict[str, LimitRule] = {}
    for name, value in raw_rules.items():
        if isinstance(value, str):
            rule_text = value
        elif isinstance(value, dict) and isinstance(value.get("rule"), str):
            rule_text = value["rule"]
        else:
            raise ConfigError(f"limiter {name!r} must be a rule string or mapping")
        parsed[str(name)] = parse_rule(rule_text, name=str(name))
    return parsed


def _load_simple_yaml(text: str) -> dict[str, Any]:
    """Parse YAML config, using PyYAML when it is installed.

    PyYAML is an optional dependency: if it is importable it is used for full
    YAML support; otherwise a minimal built-in parser handles the documented
    subset so the library keeps zero required runtime dependencies.
    """

    try:
        yaml = importlib.import_module("yaml")
    except ImportError:
        return _load_minimal_yaml(text)

    loaded = yaml.safe_load(text)
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ConfigError("YAML config must be a mapping")
    return loaded


def _load_minimal_yaml(text: str) -> dict[str, Any]:
    """Parse the small YAML subset used by the sample config without PyYAML.

    Supports both the nested and the inline rule forms (the inline form mirrors
    what TOML and JSON already allow):

        limiters:
          api:
            rule: "10/sec burst 20 algorithm token"
          login: "50/min algorithm sliding-window-counter"
    """

    result: dict[str, Any] = {}
    current_section: str | None = None
    current_name: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        stripped = line.strip()
        if indent == 0 and stripped.endswith(":"):
            current_section = stripped[:-1]
            result[current_section] = {}
            current_name = None
        elif indent == 2 and current_section:
            section = result.setdefault(current_section, {})
            if not isinstance(section, dict):
                raise ConfigError("invalid YAML section")
            if stripped.endswith(":"):
                current_name = stripped[:-1]
                section[current_name] = {}
            elif ":" in stripped:
                key, value = stripped.split(":", 1)
                section[key.strip()] = value.strip().strip('"').strip("'")
                current_name = None
            else:
                raise ConfigError(f"unsupported YAML line: {raw_line}")
        elif indent >= 4 and ":" in stripped and current_section and current_name:
            key, value = stripped.split(":", 1)
            value = value.strip().strip('"').strip("'")
            section = result[current_section]
            if not isinstance(section, dict) or not isinstance(section[current_name], dict):
                raise ConfigError("invalid YAML mapping")
            section[current_name][key.strip()] = value
        else:
            raise ConfigError(f"unsupported YAML line: {raw_line}")
    return result

