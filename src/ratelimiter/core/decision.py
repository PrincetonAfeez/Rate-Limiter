"""Decision objects returned by every limiter."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Any

_logger = logging.getLogger("ratelimiter.decision")


@dataclass(frozen=True, slots=True)
class Decision:
    """Uniform result of a rate-limit request."""

    allowed: bool
    remaining: float
    retry_after: float | None
    reset_after: float | None
    limit: float
    algorithm: str
    reason: str

    def __post_init__(self) -> None:
        if self.retry_after is not None and self.retry_after < 0:
            raise ValueError("retry_after must not be negative")
        if self.reset_after is not None and self.reset_after < 0:
            raise ValueError("reset_after must not be negative")
        if self.remaining < 0:
            _logger.warning(
                "decision clamped negative remaining=%s to 0 for algorithm=%s reason=%s",
                self.remaining,
                self.algorithm,
                self.reason,
            )
            object.__setattr__(self, "remaining", 0.0)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly representation for CLI and logs."""

        return asdict(self)

