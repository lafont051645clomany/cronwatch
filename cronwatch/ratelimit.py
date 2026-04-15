"""Rate limiting for alert dispatch to prevent notification storms."""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class RateLimitConfig:
    """Configuration for alert rate limiting."""
    max_alerts: int = 5          # max alerts per window
    window_seconds: int = 3600   # rolling window size in seconds
    cooldown_seconds: int = 300  # min seconds between alerts for same job


@dataclass
class _JobWindow:
    timestamps: List[float] = field(default_factory=list)
    last_sent: float = 0.0


class RateLimiter:
    """Tracks per-job alert frequency and enforces rate limits."""

    def __init__(self, config: RateLimitConfig | None = None) -> None:
        self._cfg = config or RateLimitConfig()
        self._windows: Dict[str, _JobWindow] = defaultdict(_JobWindow)

    def _evict(self, window: _JobWindow, now: float) -> None:
        cutoff = now - self._cfg.window_seconds
        window.timestamps = [t for t in window.timestamps if t >= cutoff]

    def is_allowed(self, job_name: str) -> bool:
        """Return True if an alert for *job_name* is permitted right now."""
        now = time.time()
        w = self._windows[job_name]
        self._evict(w, now)

        if w.last_sent and (now - w.last_sent) < self._cfg.cooldown_seconds:
            return False

        if len(w.timestamps) >= self._cfg.max_alerts:
            return False

        return True

    def record(self, job_name: str) -> None:
        """Record that an alert was sent for *job_name*."""
        now = time.time()
        w = self._windows[job_name]
        self._evict(w, now)
        w.timestamps.append(now)
        w.last_sent = now

    def reset(self, job_name: str) -> None:
        """Clear rate-limit state for *job_name* (e.g. after job recovers)."""
        self._windows.pop(job_name, None)

    def status(self, job_name: str) -> dict:
        """Return a snapshot of rate-limit state for *job_name*."""
        now = time.time()
        w = self._windows[job_name]
        self._evict(w, now)
        return {
            "job": job_name,
            "alerts_in_window": len(w.timestamps),
            "max_alerts": self._cfg.max_alerts,
            "window_seconds": self._cfg.window_seconds,
            "seconds_since_last": round(now - w.last_sent, 1) if w.last_sent else None,
            "cooldown_seconds": self._cfg.cooldown_seconds,
        }
