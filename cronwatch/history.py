"""Persistent storage for job run history using a simple JSON file."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional

from cronwatch.tracker import JobRun, JobStatus

DEFAULT_HISTORY_PATH = Path(".cronwatch_history.json")


def _run_to_dict(run: JobRun) -> dict:
    return {
        "job_name": run.job_name,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "status": run.status.value,
        "exit_code": run.exit_code,
        "note": run.note,
    }


def _run_from_dict(data: dict) -> JobRun:
    from datetime import datetime

    run = JobRun(
        job_name=data["job_name"],
        started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
    )
    if data.get("finished_at"):
        run.finished_at = datetime.fromisoformat(data["finished_at"])
    run.status = JobStatus(data["status"])
    run.exit_code = data.get("exit_code")
    run.note = data.get("note")
    return run


class HistoryStore:
    """Read/write job run history to a JSON file."""

    def __init__(self, path: Path = DEFAULT_HISTORY_PATH) -> None:
        self.path = Path(path)

    def load(self) -> List[JobRun]:
        """Return all stored runs, or empty list if file absent."""
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)
        return [_run_from_dict(d) for d in raw]

    def save(self, runs: List[JobRun]) -> None:
        """Persist a list of runs to disk."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as fh:
            json.dump([_run_to_dict(r) for r in runs], fh, indent=2)

    def append(self, run: JobRun) -> None:
        """Append a single run to the history file."""
        runs = self.load()
        runs.append(run)
        self.save(runs)

    def runs_for_job(self, job_name: str) -> List[JobRun]:
        """Return only runs matching *job_name*."""
        return [r for r in self.load() if r.job_name == job_name]

    def clear(self, job_name: Optional[str] = None) -> None:
        """Remove all runs, or only those for *job_name* if provided."""
        if job_name is None:
            self.save([])
        else:
            self.save([r for r in self.load() if r.job_name != job_name])
