"""Contracts for atomic backend mutation."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

StateFactory = Callable[[float], object]
StateMutation = Callable[[object, float], Any]
