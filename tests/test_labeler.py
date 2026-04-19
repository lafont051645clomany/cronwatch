"""Tests for cronwatch.labeler."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from cronwatch.labeler import LabelRule, Labeler, default_labeler
from cronwatch.tracker import JobRun, JobStatus


def _run(
    status: JobStatus = JobStatus.SUCCESS,
    start_offset: float = 0.0,
    duration: float | None = 10.0,
) -> JobRun:
    now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    run = JobRun(job_name="test", start_time=now, status=status)
    if duration is not None:
        from datetime import timedelta
        run.end_time = now + timedelta(seconds=duration)
    return run


# --- LabelRule.matches ---

def test_rule_matches_status():
    rule = LabelRule(label="failed", status=JobStatus.FAILURE)
    assert rule.matches(_run(status=JobStatus.FAILURE))
    assert not rule.matches(_run(status=JobStatus.SUCCESS))


def test_rule_matches_min_duration():
    rule = LabelRule(label="slow", min_duration=300.0)
    assert rule.matches(_run(duration=400.0))
    assert not rule.matches(_run(duration=100.0))


def test_rule_matches_max_duration():
    rule = LabelRule(label="fast", max_duration=5.0)
    assert rule.matches(_run(duration=3.0))
    assert not rule.matches(_run(duration=10.0))


def test_rule_matches_combined():
    rule = LabelRule(label="slow-fail", status=JobStatus.FAILURE, min_duration=60.0)
    assert rule.matches(_run(status=JobStatus.FAILURE, duration=120.0))
    assert not rule.matches(_run(status=JobStatus.SUCCESS, duration=120.0))
    assert not rule.matches(_run(status=JobStatus.FAILURE, duration=10.0))


def test_rule_no_duration_skips_duration_check():
    rule = LabelRule(label="any-fail", status=JobStatus.FAILURE)
    run = _run(status=JobStatus.FAILURE, duration=None)
    assert rule.matches(run)


# --- Labeler ---

def test_label_returns_matching_labels():
    lb = Labeler()
    lb.add_rule(LabelRule(label="failed", status=JobStatus.FAILURE))
    lb.add_rule(LabelRule(label="slow", min_duration=300.0))
    run = _run(status=JobStatus.FAILURE, duration=400.0)
    labels = lb.label(run)
    assert "failed" in labels
    assert "slow" in labels


def test_label_returns_empty_when_no_match():
    lb = Labeler()
    lb.add_rule(LabelRule(label="failed", status=JobStatus.FAILURE))
    labels = lb.label(_run(status=JobStatus.SUCCESS))
    assert labels == []


def test_label_all_keys_by_run_id():
    lb = Labeler()
    lb.add_rule(LabelRule(label="fast", max_duration=5.0))
    runs = [_run(duration=2.0), _run(duration=100.0)]
    result = lb.label_all(runs)
    assert len(result) == 2
    values = list(result.values())
    assert ["fast"] in values
    assert [] in values


# --- default_labeler ---

def test_default_labeler_labels_failure():
    lb = default_labeler()
    assert "failed" in lb.label(_run(status=JobStatus.FAILURE))


def test_default_labeler_labels_slow():
    lb = default_labeler()
    assert "slow" in lb.label(_run(duration=400.0))


def test_default_labeler_labels_fast():
    lb = default_labeler()
    assert "fast" in lb.label(_run(duration=3.0))


def test_default_labeler_labels_timeout():
    lb = default_labeler()
    assert "timeout" in lb.label(_run(status=JobStatus.TIMEOUT))
