"""Tests for cronwatch.sla."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

import pytest

from cronwatch.sla import SLAConfig, SLAViolation, SLAChecker, check_sla, _window_runs
from cronwatch.tracker import JobRun, JobStatus


def _utc(**kw) -> datetime:
    return datetime.now(timezone.utc) - timedelta(**kw)


def _run(
    job_name: str = "backup",
    status: JobStatus = JobStatus.SUCCESS,
    started_at: datetime | None = None,
    duration: float | None = 10.0,
) -> JobRun:
    started = started_at or datetime.now(timezone.utc)
    r = JobRun(job_name=job_name, run_id="abc", started_at=started)
    r.status = status
    r.duration_seconds = duration
    return r


# ---------------------------------------------------------------------------
# _window_runs
# ---------------------------------------------------------------------------

def test_window_runs_excludes_old_runs():
    old = _run(started_at=_utc(hours=30))
    recent = _run(started_at=_utc(hours=1))
    result = _window_runs([old, recent], window_hours=24)
    assert recent in result
    assert old not in result


def test_window_runs_excludes_none_start():
    r = _run()
    r.started_at = None
    result = _window_runs([r], window_hours=24)
    assert result == []


# ---------------------------------------------------------------------------
# check_sla – success rate
# ---------------------------------------------------------------------------

def test_no_violation_when_rate_meets_threshold():
    runs = [_run(status=JobStatus.SUCCESS) for _ in range(9)]
    runs.append(_run(status=JobStatus.FAILURE))
    cfg = SLAConfig(job_name="backup", min_success_rate=0.80)
    violations = check_sla(cfg, runs)
    assert violations == []


def test_violation_when_rate_below_threshold():
    runs = [_run(status=JobStatus.FAILURE) for _ in range(5)]
    runs += [_run(status=JobStatus.SUCCESS) for _ in range(5)]
    cfg = SLAConfig(job_name="backup", min_success_rate=0.90)
    violations = check_sla(cfg, runs)
    assert len(violations) == 1
    assert "success rate" in violations[0].reason


def test_no_violation_when_no_runs():
    cfg = SLAConfig(job_name="backup", min_success_rate=0.95)
    assert check_sla(cfg, []) == []


# ---------------------------------------------------------------------------
# check_sla – duration
# ---------------------------------------------------------------------------

def test_no_duration_violation_when_within_limit():
    runs = [_run(duration=30.0) for _ in range(5)]
    cfg = SLAConfig(job_name="backup", min_success_rate=0.0, max_duration_seconds=60.0)
    violations = check_sla(cfg, runs)
    assert violations == []


def test_duration_violation_when_run_exceeds_limit():
    runs = [_run(duration=120.0)]
    cfg = SLAConfig(job_name="backup", min_success_rate=0.0, max_duration_seconds=60.0)
    violations = check_sla(cfg, runs)
    assert any("max duration" in v.reason for v in violations)


def test_violation_message_contains_job_name():
    runs = [_run(status=JobStatus.FAILURE) for _ in range(10)]
    cfg = SLAConfig(job_name="backup", min_success_rate=1.0)
    violations = check_sla(cfg, runs)
    assert "backup" in violations[0].message()


# ---------------------------------------------------------------------------
# SLAChecker
# ---------------------------------------------------------------------------

def test_checker_aggregates_across_configs():
    runs_a = [_run(job_name="job_a", status=JobStatus.FAILURE) for _ in range(5)]
    runs_b = [_run(job_name="job_b", duration=200.0)]
    configs = [
        SLAConfig(job_name="job_a", min_success_rate=0.9),
        SLAConfig(job_name="job_b", min_success_rate=0.0, max_duration_seconds=60.0),
    ]
    checker = SLAChecker(configs)
    violations = checker.check_all(runs_a + runs_b)
    job_names = {v.job_name for v in violations}
    assert "job_a" in job_names
    assert "job_b" in job_names


def test_checker_returns_empty_when_all_slas_met():
    runs = [_run(job_name="job_a", status=JobStatus.SUCCESS) for _ in range(10)]
    checker = SLAChecker([SLAConfig(job_name="job_a", min_success_rate=0.80)])
    assert checker.check_all(runs) == []
