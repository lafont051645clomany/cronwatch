"""Output formatters for cronwatch reports and alerts."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from cronwatch.reporter import JobSummary
from cronwatch.tracker import JobRun, JobStatus

_DATE_FMT = "%Y-%m-%d %H:%M:%S UTC"


def _fmt_dt(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime(_DATE_FMT)


def _fmt_duration(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, secs = divmod(seconds, 60)
    return f"{int(minutes)}m {secs:.0f}s"


def format_run_table(runs: List[JobRun]) -> str:
    """Return a plain-text table of individual job runs."""
    if not runs:
        return "No runs recorded."

    header = f"{'JOB':<24} {'STATUS':<10} {'STARTED':<22} {'DURATION':<12}"
    sep = "-" * len(header)
    rows = [header, sep]
    for run in runs:
        status = run.status.value if run.status else "unknown"
        rows.append(
            f"{run.job_name:<24} {status:<10} {_fmt_dt(run.started_at):<22}"
            f" {_fmt_duration(run.duration_seconds):<12}"
        )
    return "\n".join(rows)


def format_summary_table(summaries: List[JobSummary]) -> str:
    """Return a plain-text summary table across multiple jobs."""
    if not summaries:
        return "No job summaries available."

    header = (
        f"{'JOB':<24} {'RUNS':>6} {'OK':>6} {'FAIL':>6}"
        f" {'SUCCESS%':>9} {'AVG DUR':>10} {'MAX DUR':>10}"
    )
    sep = "-" * len(header)
    rows = [header, sep]
    for s in summaries:
        pct = f"{s.success_rate * 100:.1f}%"
        rows.append(
            f"{s.job_name:<24} {s.total_runs:>6} {s.successful:>6} {s.failed:>6}"
            f" {pct:>9} {_fmt_duration(s.avg_duration):>10}"
            f" {_fmt_duration(s.max_duration):>10}"
        )
    return "\n".join(rows)
