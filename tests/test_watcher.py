"""Tests for cronwatch.watcher."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.config import AlertConfig, CronwatchConfig, JobConfig
from cronwatch.tracker import JobRun, JobStatus, JobTracker
from cronwatch.watcher import Watcher


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def job_cfg() -> JobConfig:
    return JobConfig(name="backup", schedule="0 2 * * *", timeout_seconds=300)


@pytest.fixture()
def alert_cfg() -> AlertConfig:
    return AlertConfig(
        email_to="ops@example.com",
        email_from="cronwatch@example.com",
        smtp_host="localhost",
    )


@pytest.fixture()
def config(job_cfg, alert_cfg) -> CronwatchConfig:
    return CronwatchConfig(jobs=[job_cfg], alerts=alert_cfg)


@pytest.fixture()
def tracker() -> JobTracker:
    return JobTracker()


@pytest.fixture()
def watcher(config, tracker) -> Watcher:
    return Watcher(config=config, tracker=tracker)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_run(
    name: str = "backup",
    status: JobStatus = JobStatus.SUCCESS,
    minutes_ago: int = 5,
) -> JobRun:
    started = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    return JobRun(
        job_name=name,
        run_id=f"{name}-001",
        started_at=started,
        finished_at=started + timedelta(minutes=1),
        status=status,
        exit_code=0 if status == JobStatus.SUCCESS else 1,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@patch("cronwatch.watcher.dispatch_alert")
def test_no_alert_for_successful_recent_run(mock_dispatch, watcher, tracker):
    run = _make_run(status=JobStatus.SUCCESS, minutes_ago=10)
    tracker._runs["backup"] = run  # type: ignore[attr-defined]

    with patch("cronwatch.watcher.is_overdue", return_value=False):
        watcher.check_all()

    mock_dispatch.assert_not_called()


@patch("cronwatch.watcher.dispatch_alert")
def test_alert_dispatched_for_failed_run(mock_dispatch, watcher, tracker):
    run = _make_run(status=JobStatus.FAILED)
    tracker._runs["backup"] = run  # type: ignore[attr-defined]

    watcher.check_all()

    mock_dispatch.assert_called_once()
    dispatched_run, _ = mock_dispatch.call_args[0]
    assert dispatched_run.job_name == "backup"
    assert dispatched_run.status == JobStatus.FAILED


@patch("cronwatch.watcher.dispatch_alert")
def test_failed_alert_not_sent_twice(mock_dispatch, watcher, tracker):
    run = _make_run(status=JobStatus.FAILED)
    tracker._runs["backup"] = run  # type: ignore[attr-defined]

    watcher.check_all()
    watcher.check_all()  # second pass — should not re-alert

    assert mock_dispatch.call_count == 1


@patch("cronwatch.watcher.dispatch_alert")
def test_alert_dispatched_when_overdue(mock_dispatch, watcher):
    with patch("cronwatch.watcher.is_overdue", return_value=True):
        watcher.check_all()

    mock_dispatch.assert_called_once()
    dispatched_run, _ = mock_dispatch.call_args[0]
    assert "overdue" in dispatched_run.run_id


@patch("cronwatch.watcher.dispatch_alert")
def test_unknown_job_logs_warning(mock_dispatch, watcher, caplog):
    import logging

    with caplog.at_level(logging.WARNING, logger="cronwatch.watcher"):
        watcher._check_job("nonexistent")

    assert "unknown job" in caplog.text
    mock_dispatch.assert_not_called()
