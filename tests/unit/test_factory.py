"""Test factory."""

from pathlib import Path

import pytest

from ratelimiter.algorithms.token_bucket import TokenBucketLimiter
from ratelimiter.core.config import LimitRule
from ratelimiter.core.decision import Decision
from ratelimiter.factory import (
    build_limiter,
    build_limiter_from_rule,
    require_inspectable,
    rule_from_config,
)


class _OpaqueLimiter:
    algorithm = "opaque"

    def try_acquire(self, key: str, cost: int | float = 1) -> Decision:
        return Decision(
            allowed=True,
            remaining=1,
            retry_after=None,
            reset_after=None,
            limit=1,
            algorithm=self.algorithm,
            reason="opaque",
        )


def test_build_limiter_all_algorithms() -> None:
    assert build_limiter("token").algorithm == "token"
    assert build_limiter("fixed-window").algorithm == "fixed-window"
    assert build_limiter("sliding-window-counter").algorithm == "sliding-window-counter"
    assert build_limiter("leaky").algorithm == "leaky"


def test_build_limiter_from_rule_unsupported_algorithm() -> None:
    rule = LimitRule(name="x", limit=1, period_seconds=1, algorithm="not-supported")
    with pytest.raises(ValueError, match="unsupported algorithm"):
        build_limiter_from_rule(rule)


def test_require_inspectable_accepts_real_limiter() -> None:
    limiter = build_limiter("token")
    assert require_inspectable(limiter) is limiter


def test_require_inspectable_rejects_opaque_limiter() -> None:
    with pytest.raises(TypeError, match="does not expose storage"):
        require_inspectable(_OpaqueLimiter())  # type: ignore[arg-type]


def test_rule_from_config_single_rule_auto_select(tmp_path: Path) -> None:
    path = tmp_path / "one.json"
    path.write_text('{"limiters": {"solo": "10/sec algorithm token"}}', encoding="utf-8")
    rule = rule_from_config(path)
    assert rule.name == "solo"


def test_rule_from_config_requires_name_when_multiple(tmp_path: Path) -> None:
    path = tmp_path / "many.json"
    path.write_text(
        '{"limiters": {"a": "10/sec algorithm token", "b": "10/sec algorithm fixed-window"}}',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="--name is required"):
        rule_from_config(path)


def test_rule_from_config_unknown_name(tmp_path: Path) -> None:
    path = tmp_path / "many.json"
    path.write_text('{"limiters": {"a": "10/sec algorithm token"}}', encoding="utf-8")
    with pytest.raises(ValueError, match="unknown limiter"):
        rule_from_config(path, "missing")


def test_rule_from_config_empty_rules(tmp_path: Path) -> None:
    path = tmp_path / "empty.json"
    path.write_text('{"limiters": {}}', encoding="utf-8")
    with pytest.raises(ValueError, match="no limiters"):
        rule_from_config(path)


def test_build_limiter_custom_refill_rate() -> None:
    limiter = build_limiter("token", limit=10, period_seconds=10, refill_rate=0)
    assert isinstance(limiter, TokenBucketLimiter)
    assert limiter.refill_rate == 0
