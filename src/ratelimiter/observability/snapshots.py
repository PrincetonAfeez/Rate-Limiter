"""Snapshot helpers for CLI display."""

from __future__ import annotations

from typing import Any


def compact_float(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 6)
    return value


def compact_mapping(mapping: dict[str, Any]) -> dict[str, Any]:
    return {key: compact_float(value) for key, value in mapping.items()}

