"""Tests for cronwatch.overlap — overlapping run detection."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

import pytest

from cronwatch.overlap import detect_overlaps, format_overlap_table, OverlapRecord
from cronwatch.tracker import JobStatus


def _utc(hour: int, minute: int = 0, second: int = 0) -> datetime:
    return datetime(2024, 1, 15, hour, minute, second, tzinfo=timezone.utc)


def _run(job_name: str, started_at, finished_at=None, run_id: str = None):
    run = MagicMock()
    run.job_name = job_name
    run.started_at = started_at
    run.finished_at = finished_at
    run.run_id = run_id or f"{job_name}-{started_at}"
    run.status = JobStatus.SUCCESS
    return run


# ---------------------------------------------------------------------------
# detect_overlaps
# ---------------------------------------------------------------------------

def test_no_overlap_sequential_runs():
    runs = [
        _run("backup", _utc(1, 0), _utc(1, 10), "r1"),
        _run("backup", _utc(1, 15), _utc(1, 25), "r2"),
    ]
    assert detect_overlaps(runs) == []


def test_detects_simple_overlap():
    runs = [
        _run("backup", _utc(1, 0), _utc(1, 20), "r1"),
        _run("backup", _utc(1, 10), _utc(1, 30), "r2"),
    ]
    records = detect_overlaps(runs)
    assert len(records) == 1
    rec = records[0]
    assert rec.job_name == "backup"
    assert rec.earlier_run_id == "r1"
    assert rec.later_run_id == "r2"
    assert rec.overlap_seconds == pytest.approx(10 * 60)


def test_overlap_record_message():
    rec = OverlapRecord(
        job_name="sync",
        earlier_run_id="a",
        later_run_id="b",
        overlap_seconds=45.0,
        earlier_started=_utc(2, 0),
        later_started=_utc(2, 0, 30),
    )
    assert "sync" in rec.message
    assert "45.0" in rec.message
    assert "b" in rec.message


def test_skips_run_without_started_at():
    r = _run("job", None, _utc(1, 10), "r1")
    assert detect_overlaps([r]) == []


def test_earlier_run_without_finished_at_not_flagged():
    """If the earlier run has no finished_at it cannot be used as anchor."""
    runs = [
        _run("job", _utc(1, 0), None, "r1"),
        _run("job", _utc(1, 5), _utc(1, 15), "r2"),
    ]
    assert detect_overlaps(runs) == []


def test_multiple_overlaps_same_job():
    runs = [
        _run("etl", _utc(1, 0), _utc(2, 0), "r1"),
        _run("etl", _utc(1, 10), _utc(1, 50), "r2"),
        _run("etl", _utc(1, 20), _utc(1, 40), "r3"),
    ]
    records = detect_overlaps(runs)
    # r2 and r3 both overlap with r1; r3 also overlaps with r2
    assert len(records) == 3


def test_different_jobs_do_not_cross_detect():
    runs = [
        _run("job_a", _utc(1, 0), _utc(1, 30), "a1"),
        _run("job_b", _utc(1, 10), _utc(1, 40), "b1"),
    ]
    assert detect_overlaps(runs) == []


# ---------------------------------------------------------------------------
# format_overlap_table
# ---------------------------------------------------------------------------

def test_format_empty_returns_message():
    assert format_overlap_table([]) == "No overlapping runs detected."


def test_format_table_contains_job_name():
    rec = OverlapRecord(
        job_name="myjob",
        earlier_run_id="aaa",
        later_run_id="bbb",
        overlap_seconds=120.0,
        earlier_started=_utc(3, 0),
        later_started=_utc(3, 1),
    )
    table = format_overlap_table([rec])
    assert "myjob" in table
    assert "120.0" in table
