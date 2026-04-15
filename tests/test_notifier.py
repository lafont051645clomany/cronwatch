"""Tests for cronwatch.notifier."""

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
from cronwatch.tracker import JobRun, JobStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def failed_run() -> JobRun:
    return JobRun(
        job_name="backup",
        started_at=datetime(2024, 1, 1, 3, 0, tzinfo=timezone.utc),
        finished_at=datetime(2024, 1, 1, 3, 5, tzinfo=timezone.utc),
        status=JobStatus.FAILURE,
        exit_code=1,
    )


@pytest.fixture()
def alert_cfg() -> AlertConfig:
    return AlertConfig(
        email_to="ops@example.com",
        email_from="cronwatch@example.com",
        smtp_host="localhost",
        smtp_port=25,
    )


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------

def test_email_channel_registered_by_default():
    assert "email" in list_channels()


def test_register_and_retrieve_custom_channel():
    handler = MagicMock(return_value=True)
    register_channel("slack", handler)
    assert get_channel("slack") is handler
    # cleanup
    from cronwatch import notifier
    notifier._REGISTRY.pop("slack", None)


def test_get_channel_returns_none_for_unknown():
    assert get_channel("__nonexistent__") is None


# ---------------------------------------------------------------------------
# notify() tests
# ---------------------------------------------------------------------------

def test_notify_uses_email_fallback_when_no_channels(failed_run, alert_cfg):
    with patch("cronwatch.notifier.dispatch_alert", return_value=True) as mock_dispatch:
        summary = notify(failed_run, alert_cfg, channels=["email"])
    mock_dispatch.assert_called_once_with(failed_run, alert_cfg)
    assert summary.all_succeeded


def test_notify_custom_channel_called(failed_run, alert_cfg):
    handler = MagicMock(return_value=True)
    register_channel("webhook", handler)
    try:
        summary = notify(failed_run, alert_cfg, channels=["webhook"])
        handler.assert_called_once_with(failed_run, alert_cfg)
        assert summary.all_succeeded
    finally:
        from cronwatch import notifier
        notifier._REGISTRY.pop("webhook", None)


def test_notify_records_failure_for_unregistered_channel(failed_run, alert_cfg):
    summary = notify(failed_run, alert_cfg, channels=["__ghost__"])
    assert not summary.all_succeeded
    assert "__ghost__" in summary.failed_channels


def test_notify_captures_handler_exception(failed_run, alert_cfg):
    def boom(run, cfg):
        raise RuntimeError("network error")

    register_channel("boom", boom)
    try:
        summary = notify(failed_run, alert_cfg, channels=["boom"])
        assert not summary.all_succeeded
        assert summary.results[0].error == "network error"
    finally:
        from cronwatch import notifier
        notifier._REGISTRY.pop("boom", None)


def test_notification_summary_failed_channels(failed_run):
    summary = NotificationSummary(run=failed_run)
    summary.results = [
        NotificationResult(channel="email", success=True),
        NotificationResult(channel="slack", success=False, error="timeout"),
    ]
    assert not summary.all_succeeded
    assert summary.failed_channels == ["slack"]
