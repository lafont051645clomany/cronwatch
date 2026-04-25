"""Heatmap: aggregate run counts and failure rates by hour-of-day and day-of-week."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cronwatch.tracker import JobRun, JobStatus

# Axes
HOURS = list(range(24))          # 0–23
DAYS  = list(range(7))           # 0=Monday … 6=Sunday


@dataclass
class HeatCell:
    total: int = 0
    failures: int = 0

    @property
    def failure_rate(self) -> Optional[float]:
        if self.total == 0:
            return None
        return self.failures / self.total


@dataclass
class Heatmap:
    """2-D grid keyed by (day_of_week, hour_of_day)."""
    job: str
    cells: Dict[tuple, HeatCell] = field(default_factory=dict)

    def _cell(self, day: int, hour: int) -> HeatCell:
        key = (day, hour)
        if key not in self.cells:
            self.cells[key] = HeatCell()
        return self.cells[key]

    def record(self, run: JobRun) -> None:
        ts = run.started_at
        if ts is None:
            return
        cell = self._cell(ts.weekday(), ts.hour)
        cell.total += 1
        if run.status == JobStatus.FAILURE:
            cell.failures += 1

    def get(self, day: int, hour: int) -> HeatCell:
        return self.cells.get((day, hour), HeatCell())


def build_heatmap(job: str, runs: List[JobRun]) -> Heatmap:
    """Build a Heatmap for *job* from the provided run list."""
    hm = Heatmap(job=job)
    for run in runs:
        if run.job_name == job:
            hm.record(run)
    return hm


def build_all_heatmaps(runs: List[JobRun]) -> Dict[str, Heatmap]:
    """Build one Heatmap per distinct job name found in *runs*."""
    jobs: Dict[str, Heatmap] = {}
    for run in runs:
        if run.job_name not in jobs:
            jobs[run.job_name] = Heatmap(job=run.job_name)
        jobs[run.job_name].record(run)
    return jobs
