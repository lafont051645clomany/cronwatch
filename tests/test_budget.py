"""Tests for cronwatch.budget and cronwatch.budget_reporter."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import pytest

from cronwatch.budget import BudgetChecker, BudgetConfig, BudgetViolation
from cronwatch.budget_reporter import format_budget_table
from cronwatch.tracker import JobRun, JobStatus


def _run(job: str, seconds: float) -> JobRun:
    start = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    from datetime import timedelta
    end = start + timedelta(seconds=seconds)
    return JobRun(
        job_name=job,
        run_id=f"run-{job}-{int(seconds)}",
        started_at=start,
        finished_at=end,
        status=JobStatus.SUCCESS,
        exit_code=0,
    )


@pytest.fixture
def checker():
    return BudgetChecker([
        BudgetConfig(job_name="backup", max_seconds=60.0, warn_seconds=45.0),
        BudgetConfig(job_name="sync", max_seconds=30.0),
    ])


def test_no_violation_within_budget(checker):
    v = checker.check(_run("backup", 30.0))
    assert v is None


def test_soft_warning_triggered(checker):
    v = checker.check(_run("backup", 50.0))
    assert v is not None
    assert v.is_warning is True
    assert v.limit == 45.0
    assert "WARNING" in v.message


def test_hard_breach_triggered(checker):
    v = checker.check(_run("backup", 90.0))
    assert v is not None
    assert v.is_warning is False
    assert v.limit == 60.0
    assert "BREACH" in v.message


def test_no_config_for_job_returns_none(checker):
    v = checker.check(_run("unknown_job", 999.0))
    assert v is None


def test_no_warn_seconds_only_hard_limit():
    checker = BudgetChecker([BudgetConfig(job_name="sync", max_seconds=30.0)])
    assert checker.check(_run("sync", 25.0)) is None
    v = checker.check(_run("sync", 35.0))
    assert v is not None and not v.is_warning


def test_check_all_returns_multiple_violations(checker):
    runs = [_run("backup", 90.0), _run("sync", 50.0), _run("backup", 10.0)]
    violations = checker.check_all(runs)
    assert len(violations) == 2


def test_run_without_finish_returns_none(checker):
    run = JobRun(
        job_name="backup",
        run_id="x",
        started_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        finished_at=None,
        status=JobStatus.RUNNING,
        exit_code=None,
    )
    assert checker.check(run) is None


def test_format_budget_table_empty():
    assert format_budget_table([]) == "No budget violations."


def test_format_budget_table_contains_job_name():
    v = BudgetViolation(job_name="backup", run_id="r1", duration=90.0, limit=60.0, is_warning=False)
    table = format_budget_table([v])
    assert "backup" in table
    assert "BREACH" in table


def test_format_budget_table_breach_before_warn():
    warn = BudgetViolation("j", "r1", 50.0, 45.0, is_warning=True)
    breach = BudgetViolation("j", "r2", 90.0, 60.0, is_warning=False)
    table = format_budget_table([warn, breach])
    assert table.index("BREACH") < table.index("WARN")
