"""Tests for cronwatch.metrics and cronwatch.metrics_reporter."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import pytest

from cronwatch.tracker import JobRun, JobStatus
from cronwatch.metrics import compute_metrics, top_failing_jobs, JobMetrics
from cronwatch.metrics_reporter import format_metrics_table, format_top_failing


def _make_run(
    job_name: str,
    status: JobStatus,
    started: Optional[datetime] = None,
    finished: Optional[datetime] = None,
) -> JobRun:
    run = JobRun(job_name=job_name, started_at=started or datetime.now(timezone.utc))
    run.status = status
    run.finished_at = finished
    return run


@pytest.fixture()
def mixed_runs():
    now = datetime.now(timezone.utc)
    from datetime import timedelta

    return [
        _make_run("backup", JobStatus.SUCCESS, now, now + timedelta(seconds=10)),
        _make_run("backup", JobStatus.SUCCESS, now, now + timedelta(seconds=20)),
        _make_run("backup", JobStatus.FAILURE, now, now + timedelta(seconds=5)),
        _make_run("cleanup", JobStatus.FAILURE),
        _make_run("cleanup", JobStatus.TIMEOUT),
        _make_run("sync", JobStatus.SUCCESS, now, now + timedelta(seconds=30)),
    ]


def test_compute_metrics_counts(mixed_runs):
    m = compute_metrics(mixed_runs)
    assert m["backup"].total_runs == 3
    assert m["backup"].success_count == 2
    assert m["backup"].failure_count == 1
    assert m["cleanup"].failure_count == 1
    assert m["cleanup"].timeout_count == 1
    assert m["sync"].success_count == 1


def test_compute_metrics_success_rate(mixed_runs):
    m = compute_metrics(mixed_runs)
    assert m["backup"].success_rate == pytest.approx(2 / 3)
    assert m["sync"].success_rate == pytest.approx(1.0)


def test_compute_metrics_durations(mixed_runs):
    m = compute_metrics(mixed_runs)
    assert m["backup"].avg_duration == pytest.approx(35 / 3, rel=1e-3)
    assert m["backup"].max_duration == pytest.approx(20.0, rel=1e-3)
    assert m["backup"].min_duration == pytest.approx(5.0, rel=1e-3)


def test_compute_metrics_no_duration_for_active_run():
    run = JobRun(job_name="nightly", started_at=datetime.now(timezone.utc))
    run.status = JobStatus.SUCCESS
    run.finished_at = None
    m = compute_metrics([run])
    assert m["nightly"].avg_duration is None


def test_compute_metrics_empty_returns_empty():
    assert compute_metrics([]) == {}


def test_top_failing_jobs_order(mixed_runs):
    m = compute_metrics(mixed_runs)
    top = top_failing_jobs(m, n=2)
    assert top[0].job_name in {"backup", "cleanup"}
    assert len(top) == 2


def test_top_failing_jobs_respects_n(mixed_runs):
    m = compute_metrics(mixed_runs)
    top = top_failing_jobs(m, n=1)
    assert len(top) == 1


def test_format_metrics_table_contains_job_names(mixed_runs):
    m = compute_metrics(mixed_runs)
    table = format_metrics_table(m)
    assert "backup" in table
    assert "cleanup" in table
    assert "sync" in table


def test_format_metrics_table_empty():
    assert format_metrics_table({}) == "No metrics available."


def test_format_top_failing_empty():
    assert format_top_failing([]) == "No failures recorded."


def test_format_top_failing_shows_rank(mixed_runs):
    m = compute_metrics(mixed_runs)
    top = top_failing_jobs(m)
    output = format_top_failing(top)
    assert "1." in output
    assert "failure" in output
