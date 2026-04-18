"""Format budget violations for CLI display."""
from __future__ import annotations

from typing import List

from cronwatch.budget import BudgetViolation

_HDR = f"{'JOB':<24} {'RUN ID':<36} {'DURATION':>10} {'LIMIT':>10} {'LEVEL':<8}"
_SEP = "-" * len(_HDR)


def _row(v: BudgetViolation) -> str:
    level = "WARN" if v.is_warning else "BREACH"
    return (
        f"{v.job_name:<24} {v.run_id:<36} "
        f"{v.duration:>9.1f}s {v.limit:>9.1f}s {level:<8}"
    )


def format_budget_table(violations: List[BudgetViolation]) -> str:
    if not violations:
        return "No budget violations."
    lines = [_HDR, _SEP]
    for v in sorted(violations, key=lambda x: (x.is_warning, -x.duration)):
        lines.append(_row(v))
    return "\n".join(lines)
