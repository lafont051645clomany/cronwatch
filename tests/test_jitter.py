"""Tests for cronwatch.jitter."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from cronwatch.jitter import JitterResult, analyse_jitter, flagged
from cronwatch.tracker import JobRun, JobStatus


def _run(
    job_name: str = "backup",
    started_at: datetime | None = None,
    status: JobStatus = JobStatus.SUCCESS,
) -> JobRun:
    return JobRun(
        run_id="abc-123",
        job_name=job_name,
        started_at=started_at,
        finished_at=None,
        status=status,
        exit_code=0,
        duration_seconds=None,
        tags=[],
    )


_CRON = "0 * * * *"  # every hour on the hour


def _utc(hour: int, minute: int = 0, second: int = 0) -> datetime:
    return datetime(2024, 6, 1, hour, minute, second, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# analyse_jitter
# ---------------------------------------------------------------------------

def test_analyse_jitter_skips_run_without_start_time():
    run = _run(started_at=None)
    results = analyse_jitter([run], _CRON)
    assert results == []


def test_analyse_jitter_returns_result_per_run():
    run = _run(started_at=_utc(10, 0, 5))  # 5 s late
    with patch("cronwatch.jitter.next_run") as mock_next:
        # First call: next tick after started_at  -> 11:00
        # Second call: tick after that            -> 12:00  (interval = 3600 s)
        mock_next.side_effect = [
            _utc(11, 0, 0),
            _utc(12, 0, 0),
        ]
        results = analyse_jitter([run], _CRON, threshold_seconds=60.0)

    assert len(results) == 1
    r = results[0]
    assert r.job_name == "backup"
    assert r.run_id == "abc-123"
    # expected = 11:00 - 3600 s = 10:00:00
    assert r.expected_at == _utc(10, 0, 0)
    assert r.actual_at == _utc(10, 0, 5)
    assert r.jitter_seconds == pytest.approx(5.0)
    assert r.exceeded_threshold is False


def test_analyse_jitter_flags_large_deviation():
    run = _run(started_at=_utc(10, 5, 0))  # 5 min late
    with patch("cronwatch.jitter.next_run") as mock_next:
        mock_next.side_effect = [
            _utc(11, 0, 0),
            _utc(12, 0, 0),
        ]
        results = analyse_jitter([run], _CRON, threshold_seconds=60.0)

    assert results[0].jitter_seconds == pytest.approx(300.0)
    assert results[0].exceeded_threshold is True


def test_analyse_jitter_handles_next_run_exception():
    run = _run(started_at=_utc(10, 0, 0))
    with patch("cronwatch.jitter.next_run", side_effect=ValueError("bad expr")):
        results = analyse_jitter([run], "bad cron")
    assert results == []


# ---------------------------------------------------------------------------
# flagged
# ---------------------------------------------------------------------------

def test_flagged_returns_only_exceeded():
    ok = JitterResult("j", "1", _utc(10), _utc(10, 0, 5), 5.0, False)
    bad = JitterResult("j", "2", _utc(11), _utc(11, 5), 300.0, True)
    assert flagged([ok, bad]) == [bad]


def test_flagged_empty_when_none_exceeded():
    ok = JitterResult("j", "1", _utc(10), _utc(10, 0, 1), 1.0, False)
    assert flagged([ok]) == []
