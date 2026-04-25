"""Alert deduplication: suppress repeated alerts for the same job/status pair
within a configurable time window."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class DedupConfig:
    window_seconds: int = 3600  # suppress duplicates within this window
    max_suppressed: int = 10    # stop suppressing after this many repeats


@dataclass
class _Entry:
    first_seen: datetime
    last_seen: datetime
    count: int = 1


# key: (job_name, status)
_DedupKey = Tuple[str, str]


class DedupTracker:
    """Track alert deduplication state per (job, status) pair."""

    def __init__(self, config: DedupConfig) -> None:
        self._config = config
        self._entries: Dict[_DedupKey, _Entry] = {}

    def _evict(self, now: datetime) -> None:
        cutoff = now - timedelta(seconds=self._config.window_seconds)
        expired = [k for k, e in self._entries.items() if e.last_seen < cutoff]
        for k in expired:
            del self._entries[k]

    def is_duplicate(self, job_name: str, status: str, now: Optional[datetime] = None) -> bool:
        """Return True if this alert should be suppressed as a duplicate."""
        now = now or _now()
        self._evict(now)
        key: _DedupKey = (job_name, status)
        entry = self._entries.get(key)
        if entry is None:
            return False
        if entry.count >= self._config.max_suppressed:
            return False
        return True

    def record(self, job_name: str, status: str, now: Optional[datetime] = None) -> int:
        """Record an alert occurrence. Returns the total count for this key."""
        now = now or _now()
        self._evict(now)
        key: _DedupKey = (job_name, status)
        entry = self._entries.get(key)
        if entry is None:
            self._entries[key] = _Entry(first_seen=now, last_seen=now, count=1)
            return 1
        entry.last_seen = now
        entry.count += 1
        return entry.count

    def get_count(self, job_name: str, status: str) -> int:
        """Return current occurrence count for a (job, status) pair."""
        key: _DedupKey = (job_name, status)
        entry = self._entries.get(key)
        return entry.count if entry else 0

    def reset(self, job_name: str, status: str) -> None:
        """Clear dedup state for a specific (job, status) pair."""
        key: _DedupKey = (job_name, status)
        self._entries.pop(key, None)
