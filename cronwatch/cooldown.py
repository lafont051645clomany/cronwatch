"""Per-job cooldown tracker: suppresses repeated alerts within a quiet period."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class CooldownConfig:
    """Configuration for alert cooldown behaviour."""

    # Minimum seconds between alerts for the same job.
    period_seconds: int = 300
    # Maximum number of alerts allowed within the period (0 = unlimited after cooldown).
    max_alerts: int = 1


@dataclass
class _Entry:
    first_alert: datetime
    last_alert: datetime
    count: int = 1


class CooldownTracker:
    """Tracks per-job alert cooldown windows.

    Usage::

        tracker = CooldownTracker(CooldownConfig(period_seconds=600))
        if tracker.is_allowed("backup"):
            tracker.record("backup")
            dispatch_alert(...)
    """

    def __init__(self, config: CooldownConfig) -> None:
        self._config = config
        self._entries: Dict[str, _Entry] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_allowed(self, job_name: str, at: Optional[datetime] = None) -> bool:
        """Return True if an alert for *job_name* should be sent right now."""
        now = at or _now()
        entry = self._entries.get(job_name)
        if entry is None:
            return True
        elapsed = (now - entry.last_alert).total_seconds()
        if elapsed >= self._config.period_seconds:
            return True
        if self._config.max_alerts > 0 and entry.count < self._config.max_alerts:
            return True
        return False

    def record(self, job_name: str, at: Optional[datetime] = None) -> None:
        """Record that an alert was sent for *job_name*."""
        now = at or _now()
        entry = self._entries.get(job_name)
        if entry is None:
            self._entries[job_name] = _Entry(first_alert=now, last_alert=now)
            return
        elapsed = (now - entry.last_alert).total_seconds()
        if elapsed >= self._config.period_seconds:
            # Reset window
            self._entries[job_name] = _Entry(first_alert=now, last_alert=now)
        else:
            entry.last_alert = now
            entry.count += 1

    def reset(self, job_name: str) -> None:
        """Clear cooldown state for *job_name* (e.g. after a successful run)."""
        self._entries.pop(job_name, None)

    def status(self, job_name: str) -> Optional[_Entry]:
        """Return the current cooldown entry for *job_name*, or None."""
        return self._entries.get(job_name)

    def seconds_until_next_allowed(self, job_name: str, at: Optional[datetime] = None) -> float:
        """Return the number of seconds until an alert for *job_name* is allowed.

        Returns 0.0 if an alert is currently allowed.  Useful for surfacing
        wait times in logs or status endpoints.
        """
        now = at or _now()
        if self.is_allowed(job_name, at=now):
            return 0.0
        entry = self._entries[job_name]
        elapsed = (now - entry.last_alert).total_seconds()
        return max(0.0, self._config.period_seconds - elapsed)
