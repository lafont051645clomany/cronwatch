"""Tests for cronwatch.notifier (including rate-limit integration)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.config import AlertConfig
from cronwatch.notifier import (
    NotificationResult,
    NotificationSummary,
    get_channel,
    list_channels,
    notify,
    register_channel,
)
from cronwatch.ratelimit import RateLimitConfig, RateLimiter
from cronwatch.tracker import JobRun, JobStatus


@pytest.fixture()
def failed_run() -> JobRun:
    return JobRun(
        job_name="backup",
        started_at=datetime(2024, 1, 1, 3, 0, tzinfo=timezone.utc),
        finished_at=datetime(2024, 1, 1, 3, 5, tzinfo=timezone.utc),
        status=JobStatus.FAILED,
        exit_code=1,
    )


@pytest.fixture()
def alert_cfg() -> AlertConfig:
    return AlertConfig(email_to="ops@example.com", email_from="cron@example.com")


def test_email_channel_registered_by_default() -> None:
    assert "email" in list_channels()


def test_register_and_retrieve_custom_channel() -> None:
    fn = MagicMock(return_value=True)
    register_channel("slack", fn)
    assert get_channel("slack") is fn


def test_get_channel_returns_none_for_unknown() -> None:
    assert get_channel("__nonexistent__") is None


def test_notify_unknown_channel_records_error(
    failed_run: JobRun, alert_cfg: AlertConfig
) -> None:
    summary = notify(failed_run, alert_cfg, channels=["__ghost__"])
    assert len(summary.results) == 1
    r = summary.results[0]
    assert r.success is False
    assert r.error == "unknown channel"


def test_notify_calls_channel_fn(
    failed_run: JobRun, alert_cfg: AlertConfig
) -> None:
    fn = MagicMock(return_value=True)
    register_channel("test_ch", fn)
    summary = notify(failed_run, alert_cfg, channels=["test_ch"])
    fn.assert_called_once_with(failed_run, alert_cfg)
    assert summary.any_sent is True


def test_notify_records_exception_as_error(
    failed_run: JobRun, alert_cfg: AlertConfig
) -> None:
    def boom(run, cfg):  # noqa: ANN001
        raise RuntimeError("smtp down")

    register_channel("boom_ch", boom)
    summary = notify(failed_run, alert_cfg, channels=["boom_ch"])
    assert summary.results[0].success is False
    assert "smtp down" in (summary.results[0].error or "")


def test_notify_skips_when_rate_limited(
    failed_run: JobRun, alert_cfg: AlertConfig
) -> None:
    fn = MagicMock(return_value=True)
    register_channel("rl_ch", fn)

    limiter = RateLimiter(RateLimitConfig(max_alerts=1, window_seconds=60, cooldown_seconds=60))
    # Exhaust the limit
    limiter.record("backup")

    summary = notify(failed_run, alert_cfg, channels=["rl_ch"], rate_limiter=limiter)
    fn.assert_not_called()
    assert summary.results[0].skipped is True
    assert summary.all_skipped is True


def test_notify_records_send_with_rate_limiter(
    failed_run: JobRun, alert_cfg: AlertConfig
) -> None:
    fn = MagicMock(return_value=True)
    register_channel("rl_ok_ch", fn)

    limiter = RateLimiter(RateLimitConfig(max_alerts=5, window_seconds=60, cooldown_seconds=0))
    summary = notify(failed_run, alert_cfg, channels=["rl_ok_ch"], rate_limiter=limiter)

    assert summary.any_sent is True
    status = limiter.status("backup")
    assert status["alerts_in_window"] == 1
