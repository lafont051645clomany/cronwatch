"""Retry policy support for cron job alerts and checks."""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Callable, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class RetryPolicy:
    """Defines how retries should be attempted for a given operation."""

    max_attempts: int = 3
    delay_seconds: float = 5.0
    backoff_factor: float = 2.0
    max_delay_seconds: float = 60.0
    exceptions: tuple = field(default_factory=lambda: (Exception,))

    def delays(self) -> list[float]:
        """Return list of delay durations for each retry attempt."""
        result = []
        delay = self.delay_seconds
        for _ in range(self.max_attempts - 1):
            result.append(min(delay, self.max_delay_seconds))
            delay *= self.backoff_factor
        return result


@dataclass
class RetryResult:
    """Outcome of a retried operation."""

    success: bool
    attempts: int
    value: Any = None
    last_exception: Optional[Exception] = None


def with_retry(
    fn: Callable[[], Any],
    policy: RetryPolicy,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> RetryResult:
    """Execute *fn* according to *policy*, retrying on allowed exceptions.

    Args:
        fn: Zero-argument callable to attempt.
        policy: RetryPolicy controlling attempts and back-off.
        sleep_fn: Injectable sleep function (useful in tests).

    Returns:
        RetryResult describing the outcome.
    """
    last_exc: Optional[Exception] = None
    delays = policy.delays()

    for attempt in range(1, policy.max_attempts + 1):
        try:
            value = fn()
            logger.debug("Attempt %d succeeded.", attempt)
            return RetryResult(success=True, attempts=attempt, value=value)
        except policy.exceptions as exc:  # type: ignore[misc]
            last_exc = exc
            logger.warning(
                "Attempt %d/%d failed: %s", attempt, policy.max_attempts, exc
            )
            if attempt < policy.max_attempts:
                wait = delays[attempt - 1]
                logger.debug("Retrying in %.1f seconds...", wait)
                sleep_fn(wait)

    return RetryResult(
        success=False,
        attempts=policy.max_attempts,
        last_exception=last_exc,
    )
