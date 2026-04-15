"""Tests for cronwatch.ratelimit."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from cronwatch.ratelimit import RateLimitConfig, RateLimiter


@pytest.fixture()
def cfg() -> RateLimitConfig:
    return RateLimitConfig(max_alerts=3, window_seconds=60, cooldown_seconds=10)


@pytest.fixture()
def limiter(cfg: RateLimitConfig) -> RateLimiter:
    return RateLimiter(cfg)


def test_first_alert_is_allowed(limiter: RateLimiter) -> None:
    assert limiter.is_allowed("backup") is True


def test_record_then_cooldown_blocks(limiter: RateLimiter) -> None:
    with patch("cronwatch.ratelimit.time.time", return_value=1000.0):
        limiter.record("backup")
    # 5 s later — still within 10 s cooldown
    with patch("cronwatch.ratelimit.time.time", return_value=1005.0):
        assert limiter.is_allowed("backup") is False


def test_cooldown_expires_allows_alert(limiter: RateLimiter) -> None:
    with patch("cronwatch.ratelimit.time.time", return_value=1000.0):
        limiter.record("backup")
    with patch("cronwatch.ratelimit.time.time", return_value=1011.0):
        assert limiter.is_allowed("backup") is True


def test_max_alerts_in_window_blocks(limiter: RateLimiter) -> None:
    base = 1000.0
    for i in range(3):
        with patch("cronwatch.ratelimit.time.time", return_value=base + i * 15):
            assert limiter.is_allowed("backup") is True
            limiter.record("backup")
    # 4th attempt — window not yet expired
    with patch("cronwatch.ratelimit.time.time", return_value=base + 3 * 15):
        assert limiter.is_allowed("backup") is False


def test_window_expiry_resets_count(limiter: RateLimiter) -> None:
    base = 1000.0
    for i in range(3):
        with patch("cronwatch.ratelimit.time.time", return_value=base + i * 15):
            limiter.record("backup")
    # 61 s after first record — all timestamps evicted
    with patch("cronwatch.ratelimit.time.time", return_value=base + 61):
        assert limiter.is_allowed("backup") is True


def test_reset_clears_state(limiter: RateLimiter) -> None:
    with patch("cronwatch.ratelimit.time.time", return_value=1000.0):
        limiter.record("backup")
    limiter.reset("backup")
    with patch("cronwatch.ratelimit.time.time", return_value=1001.0):
        assert limiter.is_allowed("backup") is True


def test_different_jobs_are_independent(limiter: RateLimiter) -> None:
    with patch("cronwatch.ratelimit.time.time", return_value=1000.0):
        limiter.record("job-a")
    with patch("cronwatch.ratelimit.time.time", return_value=1001.0):
        assert limiter.is_allowed("job-b") is True


def test_status_returns_snapshot(limiter: RateLimiter) -> None:
    with patch("cronwatch.ratelimit.time.time", return_value=1000.0):
        limiter.record("backup")
    with patch("cronwatch.ratelimit.time.time", return_value=1005.0):
        s = limiter.status("backup")
    assert s["job"] == "backup"
    assert s["alerts_in_window"] == 1
    assert s["max_alerts"] == 3
    assert s["seconds_since_last"] == 5.0


def test_default_config_used_when_none_given() -> None:
    limiter = RateLimiter()
    assert limiter._cfg.max_alerts == 5
    assert limiter._cfg.window_seconds == 3600
