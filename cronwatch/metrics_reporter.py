"""Format and render job metrics as human-readable text tables."""
from __future__ import annotations

from typing import Dict, List

from cronwatch.metrics import JobMetrics

_COL_W = 14


def _pct(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.1f}%"


def _sec(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:.2f}s"


def format_metrics_table(metrics: Dict[str, JobMetrics]) -> str:
    """Render a metrics summary table."""
    if not metrics:
        return "No metrics available."

    header = (
        f"{'Job':<24} {'Runs':>{_COL_W}} {'Success':>{_COL_W}}"
        f" {'Failures':>{_COL_W}} {'Timeouts':>{_COL_W}}"
        f" {'SuccessRate':>{_COL_W}} {'AvgDur':>{_COL_W}}"
        f" {'MaxDur':>{_COL_W}}"
    )
    sep = "-" * len(header)
    rows = [header, sep]

    for m in sorted(metrics.values(), key=lambda x: x.job_name):
        row = (
            f"{m.job_name:<24} {m.total_runs:>{_COL_W}} {m.success_count:>{_COL_W}}"
            f" {m.failure_count:>{_COL_W}} {m.timeout_count:>{_COL_W}}"
            f" {_pct(m.success_rate):>{_COL_W}} {_sec(m.avg_duration):>{_COL_W}}"
            f" {_sec(m.max_duration):>{_COL_W}}"
        )
        rows.append(row)

    return "\n".join(rows)


def format_top_failing(jobs: List[JobMetrics]) -> str:
    """Render a short list of the top failing jobs."""
    if not jobs:
        return "No failures recorded."
    lines = ["Top failing jobs:", "-" * 30]
    for rank, m in enumerate(jobs, start=1):
        lines.append(f"  {rank}. {m.job_name} — {m.failure_count} failure(s)")
    return "\n".join(lines)
