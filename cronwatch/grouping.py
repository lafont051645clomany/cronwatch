"""Group job runs by arbitrary keys for batch analysis."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from cronwatch.tracker import JobRun, JobStatus


@dataclass
class RunGroup:
    """A named collection of runs sharing a common key."""
    key: str
    runs: List[JobRun] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.runs)

    @property
    def failure_count(self) -> int:
        return sum(1 for r in self.runs if r.status == JobStatus.FAILURE)

    @property
    def success_rate(self) -> Optional[float]:
        if not self.runs:
            return None
        successes = sum(1 for r in self.runs if r.status == JobStatus.SUCCESS)
        return successes / len(self.runs)

    @property
    def avg_duration(self) -> Optional[float]:
        durations = [
            r.duration_seconds()
            for r in self.runs
            if r.duration_seconds() is not None
        ]
        if not durations:
            return None
        return sum(durations) / len(durations)


def group_by(
    runs: List[JobRun],
    key_fn: Callable[[JobRun], Optional[str]],
) -> Dict[str, RunGroup]:
    """Group *runs* by the string returned by *key_fn*.

    Runs for which *key_fn* returns ``None`` are silently skipped.
    """
    groups: Dict[str, RunGroup] = defaultdict(lambda: RunGroup(key=""))
    for run in runs:
        k = key_fn(run)
        if k is None:
            continue
        if k not in groups:
            groups[k] = RunGroup(key=k)
        groups[k].runs.append(run)
    return dict(groups)


def group_by_job(runs: List[JobRun]) -> Dict[str, RunGroup]:
    """Convenience wrapper — group by ``job_name``."""
    return group_by(runs, lambda r: r.job_name)


def group_by_status(runs: List[JobRun]) -> Dict[str, RunGroup]:
    """Convenience wrapper — group by ``status.value``."""
    return group_by(runs, lambda r: r.status.value)


def group_by_date(runs: List[JobRun]) -> Dict[str, RunGroup]:
    """Convenience wrapper — group by ISO calendar date of *started_at*."""
    def _key(r: JobRun) -> Optional[str]:
        if r.started_at is None:
            return None
        return r.started_at.date().isoformat()
    return group_by(runs, _key)
