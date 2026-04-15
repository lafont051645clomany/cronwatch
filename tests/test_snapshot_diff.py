"""Tests for cronwatch.snapshot and cronwatch.diff."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from cronwatch.snapshot import (
    JobSnapshot,
    capture,
    load_snapshots,
    save_snapshots,
)
from cronwatch.diff import SnapshotDiff, changed_only, diff_snapshots
from cronwatch.tracker import JobRun, JobStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2024, 6, 1, 12, 0, 0)


def _make_run(name: str, status: JobStatus, offset_minutes: int = 0) -> JobRun:
    start = _NOW + timedelta(minutes=offset_minutes)
    run = JobRun(job_name=name, started_at=start)
    run.status = status
    run.finished_at = start + timedelta(seconds=30)
    return run


# ---------------------------------------------------------------------------
# snapshot.capture
# ---------------------------------------------------------------------------


def test_capture_empty_runs():
    snap = capture("backup", [])
    assert snap.job_name == "backup"
    assert snap.total_runs == 0
    assert snap.failure_count == 0
    assert snap.last_status is None
    assert snap.success_rate is None


def test_capture_counts_runs_and_failures():
    runs = [
        _make_run("backup", JobStatus.SUCCESS, 0),
        _make_run("backup", JobStatus.FAILED, 5),
        _make_run("backup", JobStatus.SUCCESS, 10),
    ]
    snap = capture("backup", runs)
    assert snap.total_runs == 3
    assert snap.failure_count == 1
    assert abs(snap.success_rate - 2 / 3) < 1e-9


def test_capture_last_status_reflects_most_recent_run():
    runs = [
        _make_run("job", JobStatus.SUCCESS, 0),
        _make_run("job", JobStatus.FAILED, 1),
    ]
    snap = capture("job", runs)
    assert snap.last_status == JobStatus.FAILED.value


def test_capture_ignores_other_jobs():
    runs = [
        _make_run("job_a", JobStatus.SUCCESS),
        _make_run("job_b", JobStatus.FAILED),
    ]
    snap = capture("job_a", runs)
    assert snap.total_runs == 1


# ---------------------------------------------------------------------------
# snapshot persistence
# ---------------------------------------------------------------------------


def test_save_and_load_roundtrip(tmp_path: Path):
    runs = [_make_run("nightly", JobStatus.SUCCESS)]
    snap = capture("nightly", runs)
    path = tmp_path / "snaps.json"
    save_snapshots({"nightly": snap}, path)
    loaded = load_snapshots(path)
    assert "nightly" in loaded
    assert loaded["nightly"].total_runs == 1
    assert loaded["nightly"].last_status == JobStatus.SUCCESS.value


def test_load_snapshots_returns_empty_when_no_file(tmp_path: Path):
    result = load_snapshots(tmp_path / "missing.json")
    assert result == {}


# ---------------------------------------------------------------------------
# diff.diff_snapshots
# ---------------------------------------------------------------------------


def test_diff_detects_new_job():
    current = {"new_job": capture("new_job", [_make_run("new_job", JobStatus.SUCCESS)])}
    diffs = diff_snapshots({}, current)
    assert len(diffs) == 1
    assert diffs[0].is_new_job is True


def test_diff_detects_missing_job():
    baseline = {"gone": capture("gone", [_make_run("gone", JobStatus.SUCCESS)])}
    diffs = diff_snapshots(baseline, {})
    assert diffs[0].is_missing_job is True


def test_diff_detects_status_change():
    old = capture("job", [_make_run("job", JobStatus.SUCCESS)])
    new = capture("job", [_make_run("job", JobStatus.SUCCESS), _make_run("job", JobStatus.FAILED, 1)])
    diffs = diff_snapshots({"job": old}, {"job": new})
    assert diffs[0].status_changed is True
    assert diffs[0].new_failures == 1


def test_diff_no_change_when_identical():
    snap = capture("job", [_make_run("job", JobStatus.SUCCESS)])
    diffs = diff_snapshots({"job": snap}, {"job": snap})
    assert diffs[0].has_changes is False


def test_changed_only_filters_unchanged():
    snap = capture("job", [_make_run("job", JobStatus.SUCCESS)])
    diffs = diff_snapshots({"job": snap}, {"job": snap})
    assert changed_only(diffs) == []
