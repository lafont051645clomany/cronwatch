"""Tests for cronwatch.pagerduty and cronwatch.pagerduty_reporter."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.tracker import JobRun, JobStatus
from cronwatch.pagerduty import (
    PagerDutyConfig,
    _build_payload,
    send_pagerduty_alert,
)
from cronwatch.pagerduty_reporter import format_pagerduty_results
from cronwatch.notifier import NotificationResult


_TS = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def failed_run() -> JobRun:
    return JobRun(
        run_id="abc123",
        job_name="nightly-backup",
        status=JobStatus.FAILED,
        started_at=_TS,
        finished_at=_TS,
        exit_code=1,
        error="disk full",
    )


@pytest.fixture()
def pd_cfg() -> PagerDutyConfig:
    return PagerDutyConfig(routing_key="test-key-xyz")


# ---------------------------------------------------------------------------
# _build_payload
# ---------------------------------------------------------------------------

def test_build_payload_contains_routing_key(failed_run, pd_cfg):
    payload = _build_payload(failed_run, pd_cfg)
    assert payload["routing_key"] == "test-key-xyz"


def test_build_payload_summary_includes_job_name(failed_run, pd_cfg):
    payload = _build_payload(failed_run, pd_cfg)
    assert "nightly-backup" in payload["payload"]["summary"]


def test_build_payload_severity_error_for_failure(failed_run, pd_cfg):
    payload = _build_payload(failed_run, pd_cfg)
    assert payload["payload"]["severity"] == "error"


def test_build_payload_severity_warning_for_timeout(pd_cfg):
    run = JobRun(
        run_id="t1",
        job_name="j",
        status=JobStatus.TIMEOUT,
        started_at=_TS,
        finished_at=_TS,
    )
    payload = _build_payload(run, pd_cfg)
    assert payload["payload"]["severity"] == "warning"


def test_build_payload_dedup_key_is_unique(failed_run, pd_cfg):
    payload = _build_payload(failed_run, pd_cfg)
    assert "nightly-backup" in payload["dedup_key"]
    assert "abc123" in payload["dedup_key"]


def test_build_payload_extra_details_merged(failed_run, pd_cfg):
    pd_cfg.extra_details = {"env": "prod"}
    payload = _build_payload(failed_run, pd_cfg)
    assert payload["payload"]["custom_details"]["env"] == "prod"


# ---------------------------------------------------------------------------
# send_pagerduty_alert
# ---------------------------------------------------------------------------

def test_send_returns_success_on_200(failed_run, pd_cfg):
    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.status = 202

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = send_pagerduty_alert(failed_run, pd_cfg)

    assert result.success is True
    assert "202" in (result.detail or "")


def test_send_returns_failure_on_http_error(failed_run, pd_cfg):
    import urllib.error

    with patch(
        "urllib.request.urlopen",
        side_effect=urllib.error.HTTPError(
            url="", code=400, msg="Bad Request", hdrs=None, fp=None  # type: ignore[arg-type]
        ),
    ):
        result = send_pagerduty_alert(failed_run, pd_cfg)

    assert result.success is False
    assert "400" in (result.error or "")


def test_send_returns_failure_on_network_error(failed_run, pd_cfg):
    with patch("urllib.request.urlopen", side_effect=OSError("timeout")):
        result = send_pagerduty_alert(failed_run, pd_cfg)

    assert result.success is False
    assert result.error is not None


# ---------------------------------------------------------------------------
# format_pagerduty_results
# ---------------------------------------------------------------------------

def test_format_empty_results():
    assert "No PagerDuty" in format_pagerduty_results([])


def test_format_table_contains_channel_name():
    results = [
        NotificationResult(channel="pagerduty", success=True, detail="HTTP 202")
    ]
    table = format_pagerduty_results(results)
    assert "pagerduty" in table


def test_format_table_shows_delivered_count():
    results = [
        NotificationResult(channel="pagerduty", success=True),
        NotificationResult(channel="pagerduty", success=False, error="err"),
    ]
    table = format_pagerduty_results(results)
    assert "1/2" in table
