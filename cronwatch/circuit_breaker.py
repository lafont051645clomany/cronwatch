"""Circuit breaker for cron job alerting.

Prevents alert storms by temporarily disabling notifications for a job
after a configurable number of consecutive failures.  Once the circuit
is *open* no further alerts are dispatched until the reset timeout
expires, at which point the circuit moves to *half-open* and allows a
single probe alert through.  A successful run closes the circuit again.

States
------
CLOSED  – normal operation; alerts are forwarded.
OPEN    – too many consecutive failures; alerts are suppressed.
HALF_OPEN – cooldown expired; next alert is forwarded as a probe.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Configuration for a single circuit breaker."""

    # Number of consecutive failures before the circuit opens.
    failure_threshold: int = 3
    # Seconds to wait in OPEN state before moving to HALF_OPEN.
    reset_timeout: float = 300.0


@dataclass
class _CircuitState:
    """Internal mutable state for one job's circuit."""

    state: CircuitState = CircuitState.CLOSED
    consecutive_failures: int = 0
    opened_at: Optional[float] = None  # epoch seconds


def _now() -> float:  # pragma: no cover – thin wrapper for testing
    return time.monotonic()


class CircuitBreaker:
    """Manages per-job circuit breaker state.

    Parameters
    ----------
    config:
        Default ``CircuitBreakerConfig`` applied to all jobs unless a
        per-job override is supplied via :meth:`set_job_config`.
    clock:
        Callable returning the current time as a float (seconds).  Used
        to allow deterministic testing without ``time.sleep``.
    """

    def __init__(
        self,
        config: Optional[CircuitBreakerConfig] = None,
        clock=_now,
    ) -> None:
        self._default_cfg = config or CircuitBreakerConfig()
        self._job_cfg: Dict[str, CircuitBreakerConfig] = {}
        self._states: Dict[str, _CircuitState] = {}
        self._clock = clock

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------

    def set_job_config(self, job_name: str, config: CircuitBreakerConfig) -> None:
        """Override the default config for a specific job."""
        self._job_cfg[job_name] = config

    def _cfg(self, job_name: str) -> CircuitBreakerConfig:
        return self._job_cfg.get(job_name, self._default_cfg)

    def _state(self, job_name: str) -> _CircuitState:
        if job_name not in self._states:
            self._states[job_name] = _CircuitState()
        return self._states[job_name]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def current_state(self, job_name: str) -> CircuitState:
        """Return the current circuit state for *job_name*.

        Transitions OPEN → HALF_OPEN automatically when the reset
        timeout has elapsed.
        """
        st = self._state(job_name)
        if st.state == CircuitState.OPEN:
            cfg = self._cfg(job_name)
            if st.opened_at is not None:
                elapsed = self._clock() - st.opened_at
                if elapsed >= cfg.reset_timeout:
                    st.state = CircuitState.HALF_OPEN
        return st.state

    def allow(self, job_name: str) -> bool:
        """Return ``True`` if an alert for *job_name* should be forwarded.

        CLOSED and HALF_OPEN circuits allow the alert through;
        OPEN circuits suppress it.
        """
        return self.current_state(job_name) != CircuitState.OPEN

    def record_failure(self, job_name: str) -> None:
        """Notify the breaker that *job_name* has just failed."""
        st = self._state(job_name)
        cfg = self._cfg(job_name)

        # Refresh state (may transition OPEN → HALF_OPEN)
        self.current_state(job_name)

        st.consecutive_failures += 1

        if st.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN):
            if st.consecutive_failures >= cfg.failure_threshold:
                st.state = CircuitState.OPEN
                st.opened_at = self._clock()

    def record_success(self, job_name: str) -> None:
        """Notify the breaker that *job_name* has just succeeded.

        Resets the failure counter and closes the circuit regardless of
        its current state.
        """
        st = self._state(job_name)
        st.state = CircuitState.CLOSED
        st.consecutive_failures = 0
        st.opened_at = None

    def reset(self, job_name: str) -> None:
        """Manually close the circuit and clear all counters for *job_name*."""
        if job_name in self._states:
            del self._states[job_name]
