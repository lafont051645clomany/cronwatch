"""Tests for cronwatch.heatmap and cronwatch.heatmap_reporter."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cronwatch.heatmap import (
    HeatCell,
    Heatmap,
    build_all_heatmaps,
    build_heatmap,
)
from cronwatch.heatmap_reporter import format_heatmap, format_heatmap_counts
from cronwatch.tracker import JobRun, JobStatus


def _utc(year, month, day, hour, minute=0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def _run(
    job: str,
    started: datetime,
    status: JobStatus = JobStatus.SUCCESS,
    duration: float = 10.0,
) -> JobRun:
    return JobRun(
        job_name=job,
        started_at=started,
        finished_at=started.replace(second=int(duration)),
        status=status,
        exit_code=0 if status == JobStatus.SUCCESS else 1,
    )


# ── HeatCell ─────────────────────────────────────────────────────────────────

def test_heatcell_failure_rate_none_when_no_runs():
    assert HeatCell().failure_rate is None


def test_heatcell_failure_rate_zero():
    c = HeatCell(total=5, failures=0)
    assert c.failure_rate == 0.0


def test_heatcell_failure_rate_partial():
    c = HeatCell(total=4, failures=1)
    assert c.failure_rate == pytest.approx(0.25)


# ── Heatmap.record ────────────────────────────────────────────────────────────

def test_record_increments_total():
    hm = Heatmap(job="backup")
    # Monday 2024-01-01 09:00 UTC
    hm.record(_run("backup", _utc(2024, 1, 1, 9)))
    assert hm.get(0, 9).total == 1
    assert hm.get(0, 9).failures == 0


def test_record_increments_failures():
    hm = Heatmap(job="backup")
    hm.record(_run("backup", _utc(2024, 1, 1, 9), status=JobStatus.FAILURE))
    assert hm.get(0, 9).failures == 1


def test_record_skips_run_without_started_at():
    hm = Heatmap(job="backup")
    run = JobRun(job_name="backup", started_at=None, finished_at=None,
                 status=JobStatus.FAILURE, exit_code=1)
    hm.record(run)  # must not raise
    assert sum(c.total for c in hm.cells.values()) == 0


# ── build_heatmap / build_all_heatmaps ────────────────────────────────────────

def test_build_heatmap_filters_by_job():
    runs = [
        _run("a", _utc(2024, 1, 1, 8)),
        _run("b", _utc(2024, 1, 1, 8)),
    ]
    hm = build_heatmap("a", runs)
    assert hm.get(0, 8).total == 1


def test_build_all_heatmaps_creates_one_per_job():
    runs = [
        _run("a", _utc(2024, 1, 1, 8)),
        _run("b", _utc(2024, 1, 1, 9)),
        _run("a", _utc(2024, 1, 1, 10)),
    ]
    heatmaps = build_all_heatmaps(runs)
    assert set(heatmaps.keys()) == {"a", "b"}
    assert heatmaps["a"].get(0, 8).total == 1
    assert heatmaps["a"].get(0, 10).total == 1


# ── Reporter ──────────────────────────────────────────────────────────────────

def test_format_heatmap_contains_job_name():
    hm = build_heatmap("nightly", [])
    output = format_heatmap(hm)
    assert "nightly" in output


def test_format_heatmap_has_seven_day_rows():
    hm = build_heatmap("nightly", [])
    output = format_heatmap(hm)
    for label in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
        assert label in output


def test_format_heatmap_counts_shows_nonzero():
    runs = [_run("job", _utc(2024, 1, 1, 6)) for _ in range(3)]  # 3 runs Mon 06
    hm = build_heatmap("job", runs)
    output = format_heatmap_counts(hm)
    assert " 3" in output
