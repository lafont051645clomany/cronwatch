"""Generate summary reports of cron job execution history."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from cronwatch.tracker import JobRun, JobStatus


@dataclass
class JobSummary:
    job_name: str
    total_runs: int
    successful_runs: int
    failed_runs: int
    timed_out_runs: int
    avg_duration_seconds: Optional[float]
    min_duration_seconds: Optional[float]
    max_duration_seconds: Optional[float]
    last_status: Optional[JobStatus]

    @property
    def success_rate(self) -> Optional[float]:
        if self.total_runs == 0:
            return None
        return self.successful_runs / self.total_runs * 100


def summarise_runs(job_name: str, runs: List[JobRun]) -> JobSummary:
    """Compute a summary for all completed runs of a single job."""
    completed = [r for r in runs if r.status != JobStatus.RUNNING]
    successful = [r for r in completed if r.status == JobStatus.SUCCESS]
    failed = [r for r in completed if r.status == JobStatus.FAILURE]
    timed_out = [r for r in completed if r.status == JobStatus.TIMEOUT]

    durations = [
        r.duration_seconds for r in completed if r.duration_seconds is not None
    ]

    avg_dur = sum(durations) / len(durations) if durations else None
    min_dur = min(durations) if durations else None
    max_dur = max(durations) if durations else None

    last_status: Optional[JobStatus] = None
    if completed:
        last_run = max(completed, key=lambda r: r.started_at)
        last_status = last_run.status

    return JobSummary(
        job_name=job_name,
        total_runs=len(completed),
        successful_runs=len(successful),
        failed_runs=len(failed),
        timed_out_runs=len(timed_out),
        avg_duration_seconds=avg_dur,
        min_duration_seconds=min_dur,
        max_duration_seconds=max_dur,
        last_status=last_status,
    )


def format_report(summaries: List[JobSummary]) -> str:
    """Render a plain-text report for a list of job summaries."""
    if not summaries:
        return "No job data available.\n"

    lines: List[str] = ["CronWatch Job Report", "=" * 40]
    for s in summaries:
        rate = f"{s.success_rate:.1f}%" if s.success_rate is not None else "N/A"
        avg = f"{s.avg_duration_seconds:.2f}s" if s.avg_duration_seconds is not None else "N/A"
        lines.append(f"Job: {s.job_name}")
        lines.append(f"  Runs     : {s.total_runs} (success={s.successful_runs}, "
                     f"failed={s.failed_runs}, timeout={s.timed_out_runs})")
        lines.append(f"  Success  : {rate}")
        lines.append(f"  Avg Dur  : {avg}")
        lines.append(f"  Last     : {s.last_status.value if s.last_status else 'N/A'}")
        lines.append("")
    return "\n".join(lines)
