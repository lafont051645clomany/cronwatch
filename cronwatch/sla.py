"""SLA (Service Level Agreement) tracking for cron jobs.

Tracks whether jobs meet their defined success-rate and max-duration SLAs
over a rolling window, and reports violations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from cronwatch.tracker import JobRun, JobStatus


@dataclass
class SLAConfig:
    """SLA definition for a single job."""
    job_name: str
    min_success_rate: float          # 0.0 – 1.0
    max_duration_seconds: Optional[float] = None
    window_hours: float = 24.0


@dataclass
class SLAViolation:
    job_name: str
    reason: str
    measured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def message(self) -> str:
        return f"[SLA] {self.job_name}: {self.reason}"


def _window_runs(runs: List[JobRun], window_hours: float) -> List[JobRun]:
    """Return only runs that fall within the rolling window."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    return [
        r for r in runs
        if r.started_at is not None and r.started_at >= cutoff
    ]


def check_sla(cfg: SLAConfig, runs: List[JobRun]) -> List[SLAViolation]:
    """Check a job's runs against its SLA config and return any violations."""
    relevant = _window_runs(
        [r for r in runs if r.job_name == cfg.job_name],
        cfg.window_hours,
    )

    violations: List[SLAViolation] = []

    if not relevant:
        return violations

    total = len(relevant)
    successes = sum(1 for r in relevant if r.status == JobStatus.SUCCESS)
    rate = successes / total

    if rate < cfg.min_success_rate:
        violations.append(SLAViolation(
            job_name=cfg.job_name,
            reason=(
                f"success rate {rate:.1%} is below minimum {cfg.min_success_rate:.1%} "
                f"({successes}/{total} in last {cfg.window_hours}h)"
            ),
        ))

    if cfg.max_duration_seconds is not None:
        breaches = [
            r for r in relevant
            if r.duration_seconds is not None
            and r.duration_seconds > cfg.max_duration_seconds
        ]
        if breaches:
            worst = max(r.duration_seconds for r in breaches)  # type: ignore[arg-type]
            violations.append(SLAViolation(
                job_name=cfg.job_name,
                reason=(
                    f"{len(breaches)} run(s) exceeded max duration "
                    f"{cfg.max_duration_seconds}s (worst: {worst:.1f}s)"
                ),
            ))

    return violations


class SLAChecker:
    """Evaluates multiple SLA configs against a shared run list."""

    def __init__(self, configs: List[SLAConfig]) -> None:
        self._configs = configs

    def check_all(self, runs: List[JobRun]) -> List[SLAViolation]:
        violations: List[SLAViolation] = []
        for cfg in self._configs:
            violations.extend(check_sla(cfg, runs))
        return violations
