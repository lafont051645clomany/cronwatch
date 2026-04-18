"""Checkpoint support: persist and retrieve the last successful run time per job."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

_ISO = "%Y-%m-%dT%H:%M:%S%z"


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


class CheckpointStore:
    """Persists the last-success timestamp for each job to a JSON file."""

    def __init__(self, path: str | Path = "cronwatch_checkpoints.json") -> None:
        self._path = Path(path)
        self._data: Dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                self._data = json.loads(self._path.read_text())
            except (json.JSONDecodeError, OSError):
                self._data = {}

    def _save(self) -> None:
        self._path.write_text(json.dumps(self._data, indent=2))

    def set(self, job_name: str, ts: Optional[datetime] = None) -> None:
        """Record a successful completion for *job_name* at *ts* (default: now)."""
        ts = ts or _now()
        self._data[job_name] = ts.strftime(_ISO)
        self._save()

    def get(self, job_name: str) -> Optional[datetime]:
        """Return the last success time for *job_name*, or None if never recorded."""
        raw = self._data.get(job_name)
        if raw is None:
            return None
        return datetime.strptime(raw, _ISO)

    def remove(self, job_name: str) -> None:
        """Delete the checkpoint for *job_name* if it exists."""
        if job_name in self._data:
            del self._data[job_name]
            self._save()

    def all(self) -> Dict[str, datetime]:
        """Return all checkpoints as a mapping of job name -> datetime."""
        result = {}
        for name, raw in self._data.items():
            try:
                result[name] = datetime.strptime(raw, _ISO)
            except ValueError:
                pass
        return result

    def clear(self) -> None:
        """Remove all checkpoints."""
        self._data = {}
        self._save()
