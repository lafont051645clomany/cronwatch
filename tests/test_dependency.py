"""Tests for cronwatch.dependency."""
from datetime import datetime, timedelta

import pytest

from cronwatch.tracker import JobRun, JobStatus
from cronwatch.dependency import (
    DependencyConfig,
    DependencyChecker,
    check_dependencies,
    _latest_success,
)


def _run(job: str, status: JobStatus, finished_at: datetime) -> JobRun:
    r = JobRun(job_name=job, run_id="x", started_at=finished_at - timedelta(seconds=10))
    r.status = status
    r.finished_at = finished_at
    return r


NOW = datetime(2024, 6, 1, 12, 0, 0)


@pytest.fixture
def runs():
    return [
        _run("etl", JobStatus.SUCCESS, NOW - timedelta(seconds=300)),
        _run("etl", JobStatus.FAILURE, NOW - timedelta(seconds=100)),
        _run("load", JobStatus.SUCCESS, NOW - timedelta(seconds=50)),
    ]


def test_latest_success_returns_most_recent(runs):
    result = _latest_success(runs, "etl")
    assert result == NOW - timedelta(seconds=300)


def test_latest_success_none_when_no_job(runs):
    assert _latest_success(runs, "missing") is None


def test_no_violations_when_deps_satisfied(runs):
    cfg = DependencyConfig(job="report", depends_on=["etl", "load"], max_lag_seconds=600)
    run = _run("report", JobStatus.SUCCESS, NOW)
    violations = check_dependencies(run, cfg, runs, now=NOW)
    assert violations == []


def test_violation_when_dep_never_ran(runs):
    cfg = DependencyConfig(job="report", depends_on=["missing_job"], max_lag_seconds=600)
    run = _run("report", JobStatus.SUCCESS, NOW)
    violations = check_dependencies(run, cfg, runs, now=NOW)
    assert len(violations) == 1
    assert violations[0].missing_dep == "missing_job"
    assert "never completed" in violations[0].reason


def test_violation_when_dep_too_stale(runs):
    cfg = DependencyConfig(job="report", depends_on=["etl"], max_lag_seconds=60)
    run = _run("report", JobStatus.SUCCESS, NOW)
    violations = check_dependencies(run, cfg, runs, now=NOW)
    assert len(violations) == 1
    assert "300s ago" in violations[0].reason


def test_no_config_returns_no_violations(runs):
    checker = DependencyChecker()
    run = _run("report", JobStatus.SUCCESS, NOW)
    assert checker.check(run, runs) == []


def test_checker_register_and_check(runs):
    checker = DependencyChecker()
    checker.register(DependencyConfig(job="report", depends_on=["load"], max_lag_seconds=600))
    run = _run("report", JobStatus.SUCCESS, NOW)
    violations = checker.check(run, runs)
    assert violations == []


def test_checker_multiple_jobs_isolated(runs):
    checker = DependencyChecker()
    checker.register(DependencyConfig(job="a", depends_on=["missing"], max_lag_seconds=60))
    checker.register(DependencyConfig(job="b", depends_on=["load"], max_lag_seconds=600))
    run_a = _run("a", JobStatus.SUCCESS, NOW)
    run_b = _run("b", JobStatus.SUCCESS, NOW)
    assert len(checker.check(run_a, runs)) == 1
    assert len(checker.check(run_b, runs)) == 0
