"""Exponential back-off tracker for per-job alert suppression.

Each time an alert fires for a job the *back-off window* doubles (up to a
configured ceiling).  Once the window expires the counter resets so a
persistent failure still surfaces eventually.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class BackoffConfig:
    base_seconds: float = 60.0      # first suppression window
    max_seconds: float = 3600.0     # ceiling for the window
    multiplier: float = 2.0         # growth factor per alert


@dataclass
class _State:
    window: float          # current suppression window in seconds
    last_alert_at: float   # epoch when the last alert fired
    count: int = 1         # number of consecutive suppressed alerts


def _now() -> float:  # pragma: no cover – thin wrapper for testing
    return time.monotonic()


class BackoffTracker:
    """Tracks per-job back-off state."""

    def __init__(self, config: BackoffConfig) -> None:
        self._cfg = config
        self._states: Dict[str, _State] = {}

    # ------------------------------------------------------------------
    def is_suppressed(self, job: str, *, now: Optional[float] = None) -> bool:
        """Return True if the alert for *job* should be suppressed."""
        now = now if now is not None else _now()
        state = self._states.get(job)
        if state is None:
            return False
        return (now - state.last_alert_at) < state.window

    def record(self, job: str, *, now: Optional[float] = None) -> float:
        """Record that an alert fired for *job*; return the new window size."""
        now = now if now is not None else _now()
        state = self._states.get(job)
        if state is None:
            new_window = self._cfg.base_seconds
            self._states[job] = _State(window=new_window, last_alert_at=now)
        else:
            new_window = min(
                state.window * self._cfg.multiplier, self._cfg.max_seconds
            )
            self._states[job] = _State(
                window=new_window,
                last_alert_at=now,
                count=state.count + 1,
            )
        return new_window

    def reset(self, job: str) -> None:
        """Clear back-off state for *job* (e.g. after a successful run)."""
        self._states.pop(job, None)

    def state(self, job: str) -> Optional[_State]:
        """Return the current state for *job*, or None if unseen."""
        return self._states.get(job)

    def jobs(self) -> list[str]:
        """Return names of all jobs with active back-off state."""
        return list(self._states.keys())
