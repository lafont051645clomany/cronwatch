"""Prune old entries from the history store based on age or count."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from cronwatch.history import HistoryStore
from cronwatch.tracker import JobRun


def prune_by_age(store: HistoryStore, max_age_days: int) -> int:
    """Remove runs older than *max_age_days*. Returns count of removed runs."""
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=max_age_days)
    runs = store.load()
    kept = [r for r in runs if r.started_at and r.started_at >= cutoff]
    removed = len(runs) - len(kept)
    if removed:
        store.save(kept)
    return removed


def prune_by_count(
    store: HistoryStore,
    max_runs: int,
    job_name: Optional[str] = None,
) -> int:
    """Keep only the *max_runs* most recent runs (globally or per job).

    Returns the count of removed runs.
    """
    all_runs = store.load()

    if job_name is None:
        sorted_runs = sorted(
            all_runs, key=lambda r: r.started_at or datetime.min.replace(tzinfo=timezone.utc)
        )
        removed = max(0, len(sorted_runs) - max_runs)
        store.save(sorted_runs[removed:])
        return removed

    other = [r for r in all_runs if r.job_name != job_name]
    job_runs = [r for r in all_runs if r.job_name == job_name]
    job_runs.sort(key=lambda r: r.started_at or datetime.min.replace(tzinfo=timezone.utc))
    removed = max(0, len(job_runs) - max_runs)
    store.save(other + job_runs[removed:])
    return removed


def prune_all(
    store: HistoryStore,
    max_age_days: Optional[int] = None,
    max_runs: Optional[int] = None,
    job_name: Optional[str] = None,
) -> dict:
    """Convenience wrapper: apply age and/or count pruning in one call."""
    result = {"by_age": 0, "by_count": 0}
    if max_age_days is not None:
        result["by_age"] = prune_by_age(store, max_age_days)
    if max_runs is not None:
        result["by_count"] = prune_by_count(store, max_runs, job_name=job_name)
    return result
