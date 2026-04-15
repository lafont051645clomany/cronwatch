"""Cron schedule parsing and next-run calculation utilities."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from croniter import croniter

from cronwatch.config import JobConfig


def next_run(job: JobConfig, after: Optional[datetime] = None) -> datetime:
    """Return the next scheduled run time for *job* after *after*.

    Args:
        job: The job configuration containing a cron ``schedule`` string.
        after: The reference datetime (UTC).  Defaults to ``datetime.now(UTC)``.

    Returns:
        A timezone-aware UTC datetime for the next scheduled execution.
    """
    base = after or datetime.now(timezone.utc)
    # croniter works with naive datetimes; strip tz, then re-attach.
    base_naive = base.replace(tzinfo=None)
    itr = croniter(job.schedule, base_naive)
    next_naive: datetime = itr.get_next(datetime)
    return next_naive.replace(tzinfo=timezone.utc)


def is_overdue(job: JobConfig, last_started: Optional[datetime]) -> bool:
    """Return True when *job* has not started within its expected window.

    A job is considered overdue when:
    - It has never run (``last_started`` is ``None``), OR
    - The next expected start time has passed by more than
      ``job.timeout_seconds`` seconds.

    Args:
        job: Job configuration (must have ``schedule`` and ``timeout_seconds``).
        last_started: The UTC datetime of the most recent start, or ``None``.

    Returns:
        ``True`` if the job is overdue, ``False`` otherwise.
    """
    now = datetime.now(timezone.utc)

    if last_started is None:
        # Never ran — check whether the first scheduled slot has already passed.
        # Use a reference point 1 year in the past so we get the "last" slot.
        from datetime import timedelta

        ref = now - timedelta(days=365)
        ref_job = type(job)(  # shallow copy with same schedule
            name=job.name,
            schedule=job.schedule,
            timeout_seconds=job.timeout_seconds,
            command=job.command,
        )
        expected = next_run(ref_job, after=ref)
        deadline = expected.timestamp() + job.timeout_seconds
        return now.timestamp() > deadline

    expected = next_run(job, after=last_started)
    deadline = expected.timestamp() + job.timeout_seconds
    return now.timestamp() > deadline


def describe_schedule(job: JobConfig) -> str:
    """Return a human-readable description of *job*'s cron schedule."""
    descriptions = {
        "* * * * *": "every minute",
        "0 * * * *": "every hour",
        "0 0 * * *": "daily at midnight",
        "0 9 * * 1-5": "weekdays at 09:00",
        "0 0 * * 0": "weekly on Sunday at midnight",
        "0 0 1 * *": "monthly on the 1st at midnight",
    }
    return descriptions.get(job.schedule, f"cron({job.schedule})")
