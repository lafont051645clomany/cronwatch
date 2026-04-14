"""Tests for cronwatch.alerts."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.alerts import dispatch_alert, send_email_alert, _build_subject, _build_body
from cronwatch.config import AlertConfig
from cronwatch.tracker import JobRun, JobStatus


@pytest.fixture()
def failed_run() -> JobRun:
    run = JobRun(job_name="db-backup")
    run.started_at = datetime(2024, 1, 15, 2, 0, 0)
    run.finished_at = datetime(2024, 1, 15, 2, 1, 30)
    run.exit_code = 1
    run.status = JobStatus.FAILED
    return run


@pytest.fixture()
def alert_cfg() -> AlertConfig:
    return AlertConfig(
        email_to=["ops@example.com"],
        smtp_host="smtp.example.com",
        smtp_port=587,
        email_from="cronwatch@example.com",
    )


def test_build_subject_failed(failed_run):
    assert _build_subject(failed_run) == "[cronwatch] FAILED: db-backup"


def test_build_subject_timeout():
    run = JobRun(job_name="sync")
    run.status = JobStatus.TIMEOUT
    assert _build_subject(run) == "[cronwatch] TIMEOUT: sync"


def test_build_body_contains_key_fields(failed_run):
    body = _build_body(failed_run)
    assert "db-backup" in body
    assert "failed" in body
    assert "90.0s" in body
    assert "Exit code: 1" in body


def test_send_email_alert_success(failed_run, alert_cfg):
    with patch("cronwatch.alerts.smtplib.SMTP") as mock_smtp:
        instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = instance
        result = send_email_alert(failed_run, alert_cfg)
    assert result is True
    instance.send_message.assert_called_once()


def test_send_email_alert_skipped_when_no_host(failed_run):
    cfg = AlertConfig(email_to=["ops@example.com"], smtp_host=None)
    result = send_email_alert(failed_run, cfg)
    assert result is False


def test_send_email_alert_skipped_when_no_recipients(failed_run):
    cfg = AlertConfig(email_to=[], smtp_host="smtp.example.com")
    result = send_email_alert(failed_run, cfg)
    assert result is False


def test_dispatch_alert_calls_email_on_failure(failed_run, alert_cfg):
    with patch("cronwatch.alerts.send_email_alert") as mock_send:
        dispatch_alert(failed_run, alert_cfg)
    mock_send.assert_called_once_with(failed_run, alert_cfg)


def test_dispatch_alert_skips_success(alert_cfg):
    run = JobRun(job_name="cleanup")
    run.status = JobStatus.SUCCESS
    with patch("cronwatch.alerts.send_email_alert") as mock_send:
        dispatch_alert(run, alert_cfg)
    mock_send.assert_not_called()
