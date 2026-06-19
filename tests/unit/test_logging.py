"""Test logging."""

import json
import logging

from ratelimiter.observability.logging import get_logger, log_event


def test_get_logger_returns_named_logger() -> None:
    logger = get_logger("ratelimiter.test.logging")
    assert logger.name == "ratelimiter.test.logging"


def test_log_event_emits_json_payload(caplog) -> None:  # type: ignore[no-untyped-def]
    logger = get_logger("ratelimiter.test.events")
    with caplog.at_level(logging.INFO, logger=logger.name):
        log_event(logger, "unit.test", key="user", allowed=True)
    assert caplog.records
    payload = json.loads(caplog.records[0].message)
    assert payload["event"] == "unit.test"
    assert payload["key"] == "user"
