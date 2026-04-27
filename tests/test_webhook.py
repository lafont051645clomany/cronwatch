"""Tests for cronwatch.webhook."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.tracker import JobRun, JobStatus
from cronwatch.webhook import WebhookConfig, WebhookResult, _build_payload, send_webhook

_UTC = timezone.utc


@pytest.fixture()
def failed_run() -> JobRun:
    return JobRun(
        job_name="backup",
        status=JobStatus.FAILED,
        started_at=datetime(2024, 1, 10, 3, 0, tzinfo=_UTC),
        finished_at=datetime(2024, 1, 10, 3, 5, tzinfo=_UTC),
        exit_code=1,
        error="disk full",
    )


@pytest.fixture()
def wh_cfg() -> WebhookConfig:
    return WebhookConfig(url="https://example.com/hook")


def test_build_payload_contains_job_name(failed_run, wh_cfg):
    payload = _build_payload(failed_run, wh_cfg)
    assert payload["job"] == "backup"


def test_build_payload_contains_status(failed_run, wh_cfg):
    payload = _build_payload(failed_run, wh_cfg)
    assert payload["status"] == "failed"


def test_build_payload_includes_details_by_default(failed_run, wh_cfg):
    payload = _build_payload(failed_run, wh_cfg)
    assert "started_at" in payload
    assert "exit_code" in payload
    assert payload["error"] == "disk full"


def test_build_payload_omits_details_when_disabled(failed_run):
    cfg = WebhookConfig(url="https://example.com/hook", include_run_details=False)
    payload = _build_payload(failed_run, cfg)
    assert "started_at" not in payload
    assert "exit_code" not in payload


def test_send_webhook_success(failed_run, wh_cfg):
    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.status = 200

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = send_webhook(failed_run, wh_cfg)

    assert result.success is True
    assert result.status_code == 200
    assert result.error is None


def test_send_webhook_http_error(failed_run, wh_cfg):
    import urllib.error

    with patch(
        "urllib.request.urlopen",
        side_effect=urllib.error.HTTPError(
            url="https://example.com/hook",
            code=500,
            msg="Server Error",
            hdrs=None,  # type: ignore[arg-type]
            fp=None,
        ),
    ):
        result = send_webhook(failed_run, wh_cfg)

    assert result.success is False
    assert result.status_code == 500
    assert result.error is not None


def test_send_webhook_connection_error(failed_run, wh_cfg):
    with patch(
        "urllib.request.urlopen", side_effect=OSError("connection refused")
    ):
        result = send_webhook(failed_run, wh_cfg)

    assert result.success is False
    assert result.status_code is None
    assert "connection refused" in (result.error or "")
