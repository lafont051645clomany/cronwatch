"""Tests for cronwatch.stagger."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cronwatch.stagger import (
    StaggerConfig,
    StaggerViolation,
    detect_stagger,
    group_violations_by_pair,
)
from cronwatch.tracker import JobRun, JobStatus


def _utc(hour: int = 0, minute: int = 0, second: int = 0) -> datetime:
    return datetime(2024, 1, 1, hour, minute, second, tzinfo=timezone.utc)


def _run(job: str, start: datetime) -> JobRun:
    return JobRun(
        job_name=job,
        run_id="r1",
        started_at=start,
        finished_at=None,
        status=JobStatus.SUCCESS,
        exit_code=0,
        tags=[],
    )


@pytest.fixture
def cfg() -> StaggerConfig:
    return StaggerConfig(min_gap_seconds=30.0, window_seconds=300.0)


def test_no_violations_when_jobs_well_spaced(cfg):
    runs = [
        _run("job_a", _utc(0, 0, 0)),
        _run("job_b", _utc(0, 1, 0)),  # 60 s gap
    ]
    assert detect_stagger(runs, cfg) == []


def test_violation_when_jobs_start_too_close(cfg):
    runs = [
        _run("job_a", _utc(0, 0, 0)),
        _run("job_b", _utc(0, 0, 10)),  # 10 s gap < 30 s min
    ]
    violations = detect_stagger(runs, cfg)
    assert len(violations) == 1
    assert violations[0].job_a == "job_a"
    assert violations[0].job_b == "job_b"
    assert violations[0].overlap_seconds == pytest.approx(10.0)


def test_same_job_name_not_flagged(cfg):
    runs = [
        _run("job_a", _utc(0, 0, 0)),
        _run("job_a", _utc(0, 0, 5)),
    ]
    assert detect_stagger(runs, cfg) == []


def test_outside_window_not_flagged(cfg):
    runs = [
        _run("job_a", _utc(0, 0, 0)),
        _run("job_b", _utc(0, 6, 0)),  # 360 s > 300 s window
    ]
    assert detect_stagger(runs, cfg) == []


def test_run_without_start_time_skipped(cfg):
    r = JobRun(
        job_name="job_a",
        run_id="r1",
        started_at=None,
        finished_at=None,
        status=JobStatus.FAILURE,
        exit_code=1,
        tags=[],
    )
    runs = [r, _run("job_b", _utc(0, 0, 5))]
    assert detect_stagger(runs, cfg) == []


def test_violation_message_contains_job_names():
    v = StaggerViolation(
        job_a="alpha",
        job_b="beta",
        overlap_seconds=12.5,
        at=_utc(0, 0, 0),
    )
    msg = v.message()
    assert "alpha" in msg
    assert "beta" in msg
    assert "12.5" in msg


def test_group_violations_by_pair():
    t = _utc()
    vs = [
        StaggerViolation("a", "b", 5.0, t),
        StaggerViolation("a", "b", 8.0, t),
        StaggerViolation("a", "c", 3.0, t),
    ]
    groups = group_violations_by_pair(vs)
    assert len(groups[("a", "b")]) == 2
    assert len(groups[("a", "c")]) == 1
