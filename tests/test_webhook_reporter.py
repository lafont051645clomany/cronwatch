"""Tests for cronwatch.webhook_reporter."""
from __future__ import annotations

import pytest

from cronwatch.webhook import WebhookResult
from cronwatch.webhook_reporter import format_webhook_results


@pytest.fixture()
def success_result() -> WebhookResult:
    return WebhookResult(
        url="https://example.com/hook",
        status_code=200,
        success=True,
    )


@pytest.fixture()
def failure_result() -> WebhookResult:
    return WebhookResult(
        url="https://other.com/hook",
        status_code=503,
        success=False,
        error="Service Unavailable",
    )


def test_empty_returns_message():
    output = format_webhook_results([])
    assert "No webhook" in output


def test_table_contains_url(success_result):
    output = format_webhook_results([success_result])
    assert "example.com" in output


def test_table_shows_ok_yes_for_success(success_result):
    output = format_webhook_results([success_result])
    assert "yes" in output


def test_table_shows_ok_no_for_failure(failure_result):
    output = format_webhook_results([failure_result])
    assert "no" in output


def test_table_shows_status_code(success_result):
    output = format_webhook_results([success_result])
    assert "200" in output


def test_table_shows_error_message(failure_result):
    output = format_webhook_results([failure_result])
    assert "Unavailable" in output


def test_table_contains_header(success_result):
    output = format_webhook_results([success_result])
    assert "URL" in output
    assert "Status" in output
