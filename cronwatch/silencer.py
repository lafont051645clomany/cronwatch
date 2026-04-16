"""Silence (mute) alerts for specific jobs during maintenance windows."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class SilenceWindow:
    job_name: str
    start: datetime
    end: datetime
    reason: str = ""

    def is_active(self, at: Optional[datetime] = None) -> bool:
        now = at or datetime.utcnow()
        return self.start <= now <= self.end


class Silencer:
    """Registry of silence windows; tells callers whether alerts should be suppressed."""

    def __init__(self) -> None:
        self._windows: List[SilenceWindow] = []

    def add(self, window: SilenceWindow) -> None:
        self._windows.append(window)

    def remove(self, job_name: str, start: datetime) -> bool:
        before = len(self._windows)
        self._windows = ._windows
            if not (w.job_name == job_name and w.start == start)
        ]
        return len(self._windows) < before

    def is_silenced(self, job_name:: Optional[datetime] = None) -> bool:
        now = at or datetime.utcnow()
        return any(
            w.job_name == job_name and w.is_active(now)\n        )

    def active_windows(self, at: Optional[datetime] = None) -> List[SilenceWindow]:
        now = at or datetime.utcnow()
        return [w for w in self._windows if w.is_active(now)]

    def all_windows(self) -> List[SilenceWindow]:
        return list(self._windows)

    def purge_expired(self, at: Optional[datetime] = None) -> int:
        now = at or datetime.utcnow()
        before = len(self._windows)
        self._windows = [w for w in self._windows if w.end >= now]
        return before - len(self._windows)
