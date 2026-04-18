"""Runtime budget tracking: flag jobs that exceed expected duration budgets."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cronwatch.tracker import JobRun, JobStatus


@dataclass
class BudgetConfig:
    job_name: str
    max_seconds: float
    warn_seconds: Optional[float] = None  # optional soft limit


@dataclass
class BudgetViolation:
    job_name: str
    run_id: str
    duration: float
    limit: float
    is_warning: bool  # True = soft warn, False = hard breach

    @property
    def message(self) -> str:
        kind = "WARNING" if self.is_warning else "BREACH"
        return (
            f"[{kind}] {self.job_name} ran for {self.duration:.1f}s "
            f"(limit {self.limit:.1f}s)"
        )


class BudgetChecker:
    def __init__(self, budgets: List[BudgetConfig]) -> None:
        self._budgets: Dict[str, BudgetConfig] = {b.job_name: b for b in budgets}

    def check(self, run: JobRun) -> Optional[BudgetViolation]:
        """Return a BudgetViolation if *run* exceeds its configured budget."""
        cfg = self._budgets.get(run.job_name)
        if cfg is None:
            return None
        duration = run.duration_seconds()
        if duration is None:
            return None
        if duration > cfg.max_seconds:
            return BudgetViolation(
                job_name=run.job_name,
                run_id=run.run_id,
                duration=duration,
                limit=cfg.max_seconds,
                is_warning=False,
            )
        if cfg.warn_seconds is not None and duration > cfg.warn_seconds:
            return BudgetViolation(
                job_name=run.job_name,
                run_id=run.run_id,
                duration=duration,
                limit=cfg.warn_seconds,
                is_warning=True,
            )
        return None

    def check_all(self, runs: List[JobRun]) -> List[BudgetViolation]:
        violations = []
        for run in runs:
            v = self.check(run)
            if v is not None:
                violations.append(v)
        return violations
