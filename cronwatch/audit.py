"""Audit log: records every alert dispatch with outcome and metadata."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class AuditEntry:
    job_name: str
    event: str          # e.g. "alert_dispatched", "alert_suppressed", "ping_received"
    status: str         # "ok" | "error" | "suppressed"
    channel: Optional[str] = None
    detail: Optional[str] = None
    timestamp: datetime = field(default_factory=_now)

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "event": self.event,
            "status": self.status,
            "channel": self.channel,
            "detail": self.detail,
            "timestamp": self.timestamp.isoformat(),
        }

    @staticmethod
    def from_dict(d: dict) -> "AuditEntry":
        return AuditEntry(
            job_name=d["job_name"],
            event=d["event"],
            status=d["status"],
            channel=d.get("channel"),
            detail=d.get("detail"),
            timestamp=datetime.fromisoformat(d["timestamp"]),
        )


class AuditLog:
    """Append-only audit log backed by a newline-delimited JSON file."""

    def __init__(self, path: str | os.PathLike = "cronwatch_audit.ndjson") -> None:
        self._path = Path(path)

    def record(self, entry: AuditEntry) -> None:
        """Append *entry* to the log file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry.to_dict()) + "\n")

    def load(self) -> List[AuditEntry]:
        """Return all entries in chronological order."""
        if not self._path.exists():
            return []
        entries: List[AuditEntry] = []
        with self._path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    entries.append(AuditEntry.from_dict(json.loads(line)))
        return entries

    def load_for_job(self, job_name: str) -> List[AuditEntry]:
        """Return entries that match *job_name* (case-insensitive)."""
        needle = job_name.lower()
        return [e for e in self.load() if e.job_name.lower() == needle]

    def clear(self) -> None:
        """Delete the log file (mainly for testing)."""
        if self._path.exists():
            self._path.unlink()
