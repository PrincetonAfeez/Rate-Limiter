"""Small structured logging helper."""

from __future__ import annotations

import json
import logging as py_logging
from typing import Any


def get_logger(name: str = "ratelimiter") -> py_logging.Logger:
    return py_logging.getLogger(name)


def log_event(
    logger: py_logging.Logger,
    event: str,
    *,
    level: int = py_logging.INFO,
    **fields: Any,
) -> None:
    payload = {"event": event, **fields}
    logger.log(level, json.dumps(payload, sort_keys=True, default=str))

