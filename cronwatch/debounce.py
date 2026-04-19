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
