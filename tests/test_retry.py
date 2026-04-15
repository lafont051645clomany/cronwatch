"""Tests for cronwatch.retry module."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from cronwatch.retry import RetryPolicy, RetryResult, with_retry


# ---------------------------------------------------------------------------
# RetryPolicy helpers
# ---------------------------------------------------------------------------

def test_delays_single_attempt():
    policy = RetryPolicy(max_attempts=1, delay_seconds=5.0)
    assert policy.delays() == []


def test_delays_three_attempts_backoff():
    policy = RetryPolicy(max_attempts=3, delay_seconds=2.0, backoff_factor=3.0)
    delays = policy.delays()
    assert len(delays) == 2
    assert delays[0] == pytest.approx(2.0)
    assert delays[1] == pytest.approx(6.0)


def test_delays_capped_by_max_delay():
    policy = RetryPolicy(
        max_attempts=4, delay_seconds=10.0, backoff_factor=10.0, max_delay_seconds=30.0
    )
    delays = policy.delays()
    assert all(d <= 30.0 for d in delays)


# ---------------------------------------------------------------------------
# with_retry — success path
# ---------------------------------------------------------------------------

def test_with_retry_succeeds_first_attempt():
    fn = MagicMock(return_value="ok")
    policy = RetryPolicy(max_attempts=3)
    sleep_fn = MagicMock()

    result = with_retry(fn, policy, sleep_fn=sleep_fn)

    assert result.success is True
    assert result.attempts == 1
    assert result.value == "ok"
    sleep_fn.assert_not_called()


def test_with_retry_succeeds_on_second_attempt():
    fn = MagicMock(side_effect=[ValueError("boom"), "recovered"])
    policy = RetryPolicy(max_attempts=3, delay_seconds=1.0)
    sleep_fn = MagicMock()

    result = with_retry(fn, policy, sleep_fn=sleep_fn)

    assert result.success is True
    assert result.attempts == 2
    assert result.value == "recovered"
    sleep_fn.assert_called_once()


# ---------------------------------------------------------------------------
# with_retry — failure path
# ---------------------------------------------------------------------------

def test_with_retry_exhausts_attempts():
    exc = RuntimeError("always fails")
    fn = MagicMock(side_effect=exc)
    policy = RetryPolicy(max_attempts=3, delay_seconds=0.0)
    sleep_fn = MagicMock()

    result = with_retry(fn, policy, sleep_fn=sleep_fn)

    assert result.success is False
    assert result.attempts == 3
    assert result.last_exception is exc
    assert sleep_fn.call_count == 2  # sleeps between attempts, not after last


def test_with_retry_only_catches_specified_exceptions():
    fn = MagicMock(side_effect=TypeError("unexpected"))
    policy = RetryPolicy(max_attempts=3, exceptions=(ValueError,))
    sleep_fn = MagicMock()

    with pytest.raises(TypeError):
        with_retry(fn, policy, sleep_fn=sleep_fn)


def test_with_retry_no_sleep_on_last_attempt():
    fn = MagicMock(side_effect=OSError("net error"))
    policy = RetryPolicy(max_attempts=2, delay_seconds=5.0)
    sleep_fn = MagicMock()

    result = with_retry(fn, policy, sleep_fn=sleep_fn)

    assert result.success is False
    assert sleep_fn.call_count == 1
