"""Stagger detection: identify jobs that consistently start too close
to each other, potentially competing for shared resources."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from cronwatch.tracker import JobRun


@dataclass
class StaggerConfig:
    """Configuration for stagger detection."""
    min_gap_seconds: float = 30.0
    window_seconds: float = 300.0


@dataclass
class StaggerViolation:
    job_a: str
    job_b: str
    overlap_seconds: float
    at: datetime

    def message(self) -> str:
        return (
            f"Jobs '{self.job_a}' and '{self.job_b}' started within "
            f"{self.overlap_seconds:.1f}s of each other at {self.at.isoformat()}"
        )


def _start_time(run: JobRun) -> Optional[datetime]:
    return run.started_at


def detect_stagger(
    runs: List[JobRun],
    cfg: StaggerConfig,
) -> List[StaggerViolation]:
    """Return violations where two different jobs started too close together."""
    violations: List[StaggerViolation] = []
    timed = [(r, _start_time(r)) for r in runs if _start_time(r) is not None]
    timed.sort(key=lambda x: x[1])  # type: ignore[arg-type]

    for i, (run_a, t_a) in enumerate(timed):
        for run_b, t_b in timed[i + 1 :]:
            assert t_a is not None and t_b is not None
            gap = (t_b - t_a).total_seconds()
            if gap > cfg.window_seconds:
                break
            if run_a.job_name == run_b.job_name:
                continue
            if gap < cfg.min_gap_seconds:
                violations.append(
                    StaggerViolation(
                        job_a=run_a.job_name,
                        job_b=run_b.job_name,
                        overlap_seconds=gap,
                        at=t_b,
                    )
                )
    return violations


def group_violations_by_pair(
    violations: List[StaggerViolation],
) -> Dict[Tuple[str, str], List[StaggerViolation]]:
    """Group violations by (job_a, job_b) pair for reporting."""
    groups: Dict[Tuple[str, str], List[StaggerViolation]] = {}
    for v in violations:
        key = (v.job_a, v.job_b)
        groups.setdefault(key, []).append(v)
    return groups
