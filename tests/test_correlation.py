"""Tests for cronwatch.correlation and cronwatch.correlation_reporter."""
from datetime import datetime, timedelta, timezone

import pytest

from cronwatch.tracker import JobRun, JobStatus
from cronwatch.correlation import correlate, CorrelationResult
from cronwatch.correlation_reporter import format_correlation_table

_NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _run(job: str, status: JobStatus, offset_seconds: float = 0) -> JobRun:
    finished = _NOW + timedelta(seconds=offset_seconds)
    r = JobRun(job_name=job, started_at=finished - timedelta(seconds=1))
    r.status = status
    r.finished_at = finished
    return r


def test_correlate_no_anchor_failures():
    anchor = [_run("a", JobStatus.SUCCESS)]
    candidates = {"b": [_run("b", JobStatus.FAILURE)]}
    assert correlate(anchor, candidates) == []


def test_correlate_finds_overlapping_failure():
    anchor = [_run("a", JobStatus.FAILURE, 0)]
    candidates = {"b": [_run("b", JobStatus.FAILURE, 30)]}
    results = correlate(anchor, candidates, window=timedelta(minutes=1))
    assert len(results) == 1
    assert results[0].related_job == "b"
    assert results[0].overlap_count == 1


def test_correlate_ignores_outside_window():
    anchor = [_run("a", JobStatus.FAILURE, 0)]
    candidates = {"b": [_run("b", JobStatus.FAILURE, 400)]}
    results = correlate(anchor, candidates, window=timedelta(minutes=1))
    assert results == []


def test_correlate_skips_anchor_job_itself():
    anchor = [_run("a", JobStatus.FAILURE, 0)]
    candidates = {"a": [_run("a", JobStatus.FAILURE, 10)]}
    assert correlate(anchor, candidates) == []


def test_correlate_sorted_by_overlap_desc():
    anchor = [
        _run("a", JobStatus.FAILURE, 0),
        _run("a", JobStatus.FAILURE, 100),
    ]
    candidates = {
        "b": [_run("b", JobStatus.FAILURE, 10)],
        "c": [
            _run("c", JobStatus.FAILURE, 10),
            _run("c", JobStatus.FAILURE, 110),
        ],
    }
    results = correlate(anchor, candidates, window=timedelta(minutes=1))
    assert results[0].related_job == "c"
    assert results[0].overlap_count == 2


def test_format_correlation_table_empty():
    assert format_correlation_table([]) == "No correlated failures found."


def test_format_correlation_table_contains_jobs():
    r = CorrelationResult(
        anchor_job="backup", related_job="cleanup", overlap_count=3, window_seconds=300
    )
    out = format_correlation_table([r])
    assert "backup" in out
    assert "cleanup" in out
    assert "3" in out
    assert "300" in out
