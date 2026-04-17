"""Job dependency tracking — ensure jobs run in expected order."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from cronwatch.tracker import JobRun, JobStatus


@dataclass
class DependencyConfig:
    job: str
    depends_on: List[str] = field(default_factory=list)
    max_lag_seconds: float = 3600.0


@dataclass
class DependencyViolation:
    job: str
    missing_dep: str
    reason: str


def _latest_success(runs: List[JobRun], job_name: str) -> Optional[datetime]:
    """Return the most recent successful finish time for *job_name*."""
    matches = [
        r.finished_at
        for r in runs
        if r.job_name == job_name
        and r.status == JobStatus.SUCCESS
        and r.finished_at is not None
    ]
    return max(matches, default=None)


def check_dependencies(
    run: JobRun,
    config: DependencyConfig,
    all_runs: List[JobRun],
    now: Optional[datetime] = None,
) -> List[DependencyViolation]:
    """Return violations for any unsatisfied dependencies of *run*."""
    if now is None:
        now = datetime.utcnow()

    violations: List[DependencyViolation] = []
    for dep in config.depends_on:
        last_ok = _latest_success(all_runs, dep)
        if last_ok is None:
            violations.append(
                DependencyViolation(
                    job=run.job_name,
                    missing_dep=dep,
                    reason=f"dependency '{dep}' has never completed successfully",
                )
            )
        elif (now - last_ok).total_seconds() > config.max_lag_seconds:
            lag = (now - last_ok).total_seconds()
            violations.append(
                DependencyViolation(
                    job=run.job_name,
                    missing_dep=dep,
                    reason=(
                        f"dependency '{dep}' last succeeded {lag:.0f}s ago "
                        f"(limit {config.max_lag_seconds:.0f}s)"
                    ),
                )
            )
    return violations


class DependencyChecker:
    """Stateful checker that holds dependency configs for multiple jobs."""

    def __init__(self) -> None:
        self._configs: Dict[str, DependencyConfig] = {}

    def register(self, config: DependencyConfig) -> None:
        self._configs[config.job] = config

    def check(self, run: JobRun, all_runs: List[JobRun]) -> List[DependencyViolation]:
        cfg = self._configs.get(run.job_name)
        if cfg is None:
            return []
        return check_dependencies(run, cfg, all_runs)
