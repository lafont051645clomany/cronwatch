"""Tests for cronwatch.stagger_reporter."""
from __future__ import annotations

from datetime import datetime, timezone

from cronwatch.stagger import StaggerViolation
from cronwatch.stagger_reporter import format_stagger_table


def _utc() -> datetime:
    return datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


def _v(job_a: str, job_b: str, gap: float) -> StaggerViolation:
    return StaggerViolation(job_a=job_a, job_b=job_b, overlap_seconds=gap, at=_utc())


def test_empty_returns_no_violations_message():
    result = format_stagger_table([])
    assert "No stagger" in result


def test_table_contains_job_names():
    vs = [_v("alpha", "beta", 10.0)]
    result = format_stagger_table(vs)
    assert "alpha" in result
    assert "beta" in result


def test_table_contains_occurrence_count():
    vs = [_v("a", "b", 5.0), _v("a", "b", 8.0)]
    result = format_stagger_table(vs)
    assert "2" in result


def test_table_shows_min_and_max_gap():
    vs = [_v("a", "b", 5.0), _v("a", "b", 20.0)]
    result = format_stagger_table(vs)
    assert "5.0" in result
    assert "20.0" in result


def test_table_contains_total_violations():
    vs = [_v("a", "b", 5.0), _v("a", "c", 7.0)]
    result = format_stagger_table(vs)
    assert "Total violations: 2" in result


def test_multiple_pairs_each_appear():
    vs = [_v("job1", "job2", 5.0), _v("job3", "job4", 9.0)]
    result = format_stagger_table(vs)
    assert "job1" in result
    assert "job3" in result
