"""RunLog: append-only per-job execution log with structured entries."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from cronwatch.tracker import JobRun, JobStatus


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class RunLogEntry:
    job_name: str
    status: str
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    duration_seconds: Optional[float]
    exit_code: Optional[int]
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_seconds": self.duration_seconds,
            "exit_code": self.exit_code,
            "note": self.note,
        }

    @staticmethod
    def from_dict(d: dict) -> "RunLogEntry":
        def _dt(v):
            return datetime.fromisoformat(v) if v else None

        return RunLogEntry(
            job_name=d["job_name"],
            status=d["status"],
            started_at=_dt(d.get("started_at")),
            finished_at=_dt(d.get("finished_at")),
            duration_seconds=d.get("duration_seconds"),
            exit_code=d.get("exit_code"),
            note=d.get("note", ""),
        )


def entry_from_run(run: JobRun, note: str = "") -> RunLogEntry:
    """Convert a JobRun into a RunLogEntry."""
    duration = run.duration_seconds() if run.finished_at else None
    return RunLogEntry(
        job_name=run.job_name,
        status=run.status.value if isinstance(run.status, JobStatus) else str(run.status),
        started_at=run.started_at,
        finished_at=run.finished_at,
        duration_seconds=duration,
        exit_code=run.exit_code,
        note=note,
    )


class RunLog:
    """Append-only JSONL log of job run entries."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def append(self, entry: RunLogEntry) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry.to_dict()) + "\n")

    def load(self, job_name: Optional[str] = None) -> List[RunLogEntry]:
        if not self._path.exists():
            return []
        entries: List[RunLogEntry] = []
        with self._path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = RunLogEntry.from_dict(json.loads(line))
                    if job_name is None or e.job_name == job_name:
                        entries.append(e)
                except (KeyError, ValueError):
                    continue
        return entries

    def clear(self) -> None:
        if self._path.exists():
            self._path.unlink()
