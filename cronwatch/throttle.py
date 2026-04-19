"""Alert throttling: suppress repeated alerts for the same job within a window."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ThrottleConfig:
    window_seconds: int = 300  # suppress duplicates within this window
    max_alerts: int = 3        # max alerts per window per job


@dataclass
class _Slot:
    timestamps: List[datetime] = field(default_factory=list)


class Throttler:
    """Track per-job alert counts and suppress when over threshold."""

    def __init__(self, config: ThrottleConfig) -> None:
        self._config = config
        self._slots: Dict[str, _Slot] = {}

    def _evict(self, slot: _Slot, cutoff: datetime) -> None:
        slot.timestamps = [t for t in slot.timestamps if t >= cutoff]

    def is_allowed(self, job_name: str, at: datetime | None = None) -> bool:
        """Return True if an alert for *job_name* should be sent."""
        now = at or _now()
        cutoff = now - timedelta(seconds=self._config.window_seconds)
        slot = self._slots.setdefault(job_name, _Slot())
        self._evict(slot, cutoff)
        return len(slot.timestamps) < self._config.max_alerts

    def record(self, job_name: str, at: datetime | None = None) -> None:
        """Record that an alert was sent for *job_name*."""
        now = at or _now()
        cutoff = now - timedelta(seconds=self._config.window_seconds)
        slot = self._slots.setdefault(job_name, _Slot())
        self._evict(slot, cutoff)
        slot.timestamps.append(now)

    def current_count(self, job_name: str, at: datetime | None = None) -> int:
        now = at or _now()
        cutoff = now - timedelta(seconds=self._config.window_seconds)
        slot = self._slots.get(job_name, _Slot())
        return sum(1 for t in slot.timestamps if t >= cutoff)

    def reset(self, job_name: str) -> None:
        """Clear throttle state for a job (e.g. after recovery)."""
        self._slots.pop(job_name, None)
