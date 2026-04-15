"""Tests for cronwatch.digest module."""

from __future__ import annotations

import datetime
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.digest import DigestConfig, _period_start, build_digest, send_digest
from cronwatch.config import CronwatchConfig, JobConfig, AlertConfig
from cronwatch.tracker import JobRun, JobStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
)
def cfg():
    return CronwatchConfig(
        jobs=[JobConfig(name="backup", schedule="0 2 * * *")],
        alerts=AlertConfig(smtp_host="localhost"),
    )


@pytest.fixture()
def digest_cfg():
    return DigestConfig(enabled=True, schedule="daily", recipient="ops@example.com")


def _make_run(name: str, status: JobStatus = JobStatus.SUCCESS,
              started_at: datetime.datetime | None = None) -> JobRun:
    run = JobRun(job_name=name)
    run.started_at = started_at or datetime.datetime.utcnow()
    run.finished_at = run.started_at + datetime.timedelta(seconds=5)
    run.status = status
    return run


# ---------------------------------------------------------------------------
# _period_start
# ---------------------------------------------------------------------------

def test_period_start_daily():
    now = datetime.datetime(2024, 6, 15, 14, 30, 0)
    result = _period_start("daily", now)
    assert result == datetime.datetime(2024, 6, 15, 0, 0, 0)


def test_period_start_hourly():
    now = datetime.datetime(2024, 6, 15, 14, 45, 22)
    result = _period_start("hourly", now)
    assert result == datetime.datetime(2024, 6, 15, 14, 0, 0)


def test_period_start_weekly():
    # 2024-06-15 is a Saturday (weekday=5); Monday should be 2024-06-10
    now = datetime.datetime(2024, 6, 15, 10, 0, 0)
    result = _period_start("weekly", now)
    assert result == datetime.datetime(2024, 6, 10, 0, 0, 0)


# ---------------------------------------------------------------------------
# build_digest
# ---------------------------------------------------------------------------

def test_build_digest_no_runs_returns_message(cfg, digest_cfg):
    with patch("cronwatch.digest.HistoryStore") as MockStore:
        MockStore.return_value.load.return_value = []
        result = build_digest(cfg, digest_cfg)
    assert "No runs" in result


def test_build_digest_includes_job_name(cfg, digest_cfg):
    now = datetime.datetime.utcnow()
    run = _make_run("backup", started_at=now)
    with patch("cronwatch.digest.HistoryStore") as MockStore:
        MockStore.return_value.load.return_value = [run]
        result = build_digest(cfg, digest_cfg, now=now)
    assert "backup" in result


def test_build_digest_filters_old_runs(cfg, digest_cfg):
    old = _make_run("backup", started_at=datetime.datetime(2000, 1, 1))
    with patch("cronwatch.digest.HistoryStore") as MockStore:
        MockStore.return_value.load.return_value = [old]
        result = build_digest(cfg, digest_cfg)
    assert "No runs" in result


# ---------------------------------------------------------------------------
# send_digest
# ---------------------------------------------------------------------------

def test_send_digest_calls_email_channel(cfg, digest_cfg):
    mock_result = MagicMock(success=True)
    mock_channel = MagicMock(return_value=mock_result)
    with patch("cronwatch.digest.HistoryStore") as MockStore, \
         patch("cronwatch.digest.get_channel", return_value=mock_channel):
        MockStore.return_value.load.return_value = []
        result = send_digest(cfg, digest_cfg)
    mock_channel.assert_called_once()
    assert result is mock_result


def test_send_digest_no_channel_returns_failure(cfg, digest_cfg):
    with patch("cronwatch.digest.HistoryStore") as MockStore, \
         patch("cronwatch.digest.get_channel", return_value=None):
        MockStore.return_value.load.return_value = []
        result = send_digest(cfg, digest_cfg)
    assert result.success is False
    assert "not registered" in result.error
