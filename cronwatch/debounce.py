"""Debounce repeated alerts for the same job within a time window."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional


@dataclass
class DebounceConfig:
    window_seconds: int = 300  # suppress repeated alerts within this window
    max_suppress: int = 10     # never suppress more than this many times in a row


@dataclass
class _State:
    first_seen: datetime
    last_seen: datetime
    suppressed: int = 0


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Debouncer:
    """Track per-job alert state and decide whether to fire or suppress."""

    def __init__(self, config: DebounceConfig) -> None:
        self._cfg = config
        self._state: Dict[str, _State] = {}

    def should_alert(self, job_name: str) -> bool:
        """Return True if the alert should be sent, False if suppressed."""
        now = _now()
        window = timedelta(seconds=self._cfg.window_seconds)
        state = self._state.get(job_name)

        if state is None:
            self._state[job_name] = _State(first_seen=now, last_seen=now)
            return True

        if now - state.last_seen > window:
            # window expired — reset and allow
            self._state[job_name] = _State(first_seen=now, last_seen=now)
            return True

        if state.suppressed >= self._cfg.max_suppress:
            # too many suppressions — let it through and reset counter
            state.last_seen = now
            state.suppressed = 0
            return True

        state.last_seen = now
        state.suppressed += 1
        return False

    def reset(self, job_name: str) -> None:
        """Clear debounce state for a job (e.g. after a successful run)."""
        self._state.pop(job_name, None)

    def state(self, job_name: str) -> Optional[_State]:
        return self._state.get(job_name)

    def active_jobs(self) -> Dict[str, _State]:
        """Return a snapshot of all jobs currently tracked by the debouncer.

        Expired entries (whose window has already elapsed) are pruned before
        returning so callers see only genuinely active suppression state.
        """
        now = _now()
        window = timedelta(seconds=self._cfg.window_seconds)
        expired = [
            name
            for name, s in self._state.items()
            if now - s.last_seen > window
        ]
        for name in expired:
            del self._state[name]
        return dict(self._state)
