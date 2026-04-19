"""Tests for cronwatch.debounce."""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from cronwatch.debounce import Debouncer, DebounceConfig

UTC = timezone.utc
T0 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def cfg():
    return DebounceConfig(window_seconds=60, max_suppress=3)


@pytest.fixture
def debouncer(cfg):
    return Debouncer(cfg)


def _at(dt):
    return patch("cronwatch.debounce._now", return_value=dt)


def test_first_alert_always_fires(debouncer):
    with _at(T0):
        assert debouncer.should_alert("backup") is True


def test_second_alert_within_window_suppressed(debouncer):
    with _at(T0):
        debouncer.should_alert("backup")
    with _at(T0 + timedelta(seconds=10)):
        assert debouncer.should_alert("backup") is False


def test_alert_after_window_expires_fires(debouncer):
    with _at(T0):
        debouncer.should_alert("backup")
    with _at(T0 + timedelta(seconds=120)):
        assert debouncer.should_alert("backup") is True


def test_suppressed_counter_increments(debouncer):
    with _at(T0):
        debouncer.should_alert("backup")
    with _at(T0 + timedelta(seconds=5)):
        debouncer.should_alert("backup")
    state = debouncer.state("backup")
    assert state is not None
    assert state.suppressed == 1


def test_max_suppress_allows_alert_through(debouncer):
    with _at(T0):
        debouncer.should_alert("backup")  # fires
    for i in range(1, 4):
        with _at(T0 + timedelta(seconds=i)):
            debouncer.should_alert("backup")  # suppressed x3
    with _at(T0 + timedelta(seconds=5)):
        result = debouncer.should_alert("backup")  # max_suppress reached
    assert result is True


def test_reset_clears_state(debouncer):
    with _at(T0):
        debouncer.should_alert("backup")
    debouncer.reset("backup")
    assert debouncer.state("backup") is None


def test_reset_allows_fresh_alert(debouncer):
    with _at(T0):
        debouncer.should_alert("backup")
    debouncer.reset("backup")
    with _at(T0 + timedelta(seconds=5)):
        assert debouncer.should_alert("backup") is True


def test_independent_jobs_tracked_separately(debouncer):
    with _at(T0):
        debouncer.should_alert("job_a")
        debouncer.should_alert("job_b")
    with _at(T0 + timedelta(seconds=10)):
        assert debouncer.should_alert("job_a") is False
        assert debouncer.should_alert("job_b") is False
    debouncer.reset("job_a")
    with _at(T0 + timedelta(seconds=15)):
        assert debouncer.should_alert("job_a") is True
        assert debouncer.should_alert("job_b") is False
