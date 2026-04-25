"""Tests for cronwatch.retention and cronwatch.retention_reporter."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cronwatch.retention import (
    RetentionConfig,
    apply_retention,
)
from cronwatch.retention_reporter import (
    format_retention_config,
    format_retention_result,
)
from cronwatch.tracker import JobRun, JobStatus


def _utc(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=timezone.utc)


def _run(
    job: str,
    status: JobStatus = JobStatus.SUCCESS,
    started: datetime | None = None,
) -> JobRun:
    r = JobRun(job_name=job)
    r.started_at = started or _utc(2024, 6, 1)
    r.status = status
    return r


# ---------------------------------------------------------------------------
# apply_retention — age-based
# ---------------------------------------------------------------------------

def test_age_drops_old_success_runs():
    now = _utc(2024, 9, 1)
    cfg = RetentionConfig(max_age_days=30, max_runs_per_job=None, keep_failures=False)
    old = _run("backup", started=_utc(2024, 7, 1))  # 62 days old
    recent = _run("backup", started=_utc(2024, 8, 20))  # 12 days old
    kept, result = apply_retention([old, recent], cfg, now=now)
    assert len(kept) == 1
    assert kept[0] is recent
    assert result.dropped == 1


def test_age_keeps_failures_when_flag_set():
    now = _utc(2024, 9, 1)
    cfg = RetentionConfig(max_age_days=30, keep_failures=True)
    old_fail = _run("backup", status=JobStatus.FAILED, started=_utc(2024, 7, 1))
    kept, result = apply_retention([old_fail], cfg, now=now)
    assert len(kept) == 1
    assert result.kept_due_to_failure == 1
    assert result.dropped == 0


def test_age_drops_old_failures_when_flag_false():
    now = _utc(2024, 9, 1)
    cfg = RetentionConfig(max_age_days=30, keep_failures=False)
    old_fail = _run("backup", status=JobStatus.FAILED, started=_utc(2024, 7, 1))
    kept, result = apply_retention([old_fail], cfg, now=now)
    assert len(kept) == 0
    assert result.dropped == 1


# ---------------------------------------------------------------------------
# apply_retention — count-based
# ---------------------------------------------------------------------------

def test_count_keeps_most_recent_runs():
    cfg = RetentionConfig(max_age_days=None, max_runs_per_job=2, keep_failures=False)
    runs = [
        _run("job", started=_utc(2024, 1, d))
        for d in range(1, 6)  # 5 runs
    ]
    kept, result = apply_retention(runs, cfg)
    assert len(kept) == 2
    assert result.dropped == 3
    # newest two should survive
    starts = {r.started_at for r in kept}
    assert _utc(2024, 1, 5) in starts
    assert _utc(2024, 1, 4) in starts


def test_count_per_job_is_independent():
    cfg = RetentionConfig(max_age_days=None, max_runs_per_job=1, keep_failures=False)
    runs = [
        _run("alpha", started=_utc(2024, 1, 1)),
        _run("alpha", started=_utc(2024, 1, 2)),
        _run("beta", started=_utc(2024, 1, 1)),
        _run("beta", started=_utc(2024, 1, 2)),
    ]
    kept, result = apply_retention(runs, cfg)
    assert len(kept) == 2
    assert result.dropped == 2


# ---------------------------------------------------------------------------
# apply_retention — no-op when unlimited
# ---------------------------------------------------------------------------

def test_no_op_when_unlimited():
    cfg = RetentionConfig(max_age_days=None, max_runs_per_job=None)
    runs = [_run("job", started=_utc(2024, d, 1)) for d in range(1, 6)]
    kept, result = apply_retention(runs, cfg)
    assert len(kept) == 5
    assert result.dropped == 0


# ---------------------------------------------------------------------------
# RetentionResult.summary
# ---------------------------------------------------------------------------

def test_result_summary_string():
    cfg = RetentionConfig(max_age_days=30)
    runs = [_run("job", started=_utc(2024, 1, 1))]
    _, result = apply_retention(runs, cfg, now=_utc(2024, 9, 1))
    assert "Retention:" in result.summary
    assert "dropped" in result.summary


# ---------------------------------------------------------------------------
# Reporter smoke tests
# ---------------------------------------------------------------------------

def test_format_retention_config_contains_policy_labels():
    cfg = RetentionConfig(max_age_days=60, max_runs_per_job=100, keep_failures=True)
    table = format_retention_config(cfg)
    assert "60" in table
    assert "100" in table
    assert "yes" in table


def test_format_retention_config_unlimited():
    cfg = RetentionConfig(max_age_days=None, max_runs_per_job=None)
    table = format_retention_config(cfg)
    assert "unlimited" in table


def test_format_retention_result_shows_counts():
    cfg = RetentionConfig(max_age_days=30)
    runs = [
        _run("job", started=_utc(2024, 1, 1)),
        _run("job", started=_utc(2024, 8, 25)),
    ]
    _, result = apply_retention(runs, cfg, now=_utc(2024, 9, 1))
    table = format_retention_result(result)
    assert "2" in table   # total_before
    assert "1" in table   # total_after
