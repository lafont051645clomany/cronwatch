"""Tests for cronwatch.suppression."""
from __future__ import annotations

import datetime
from typing import List

import pytest

from cronwatch.suppression import SuppressionRule, Suppressor
from cronwatch.tracker import JobRun, JobStatus


def _utc(hour: int = 12) -> datetime.datetime:
    return datetime.datetime(2024, 1, 15, hour, 0, 0, tzinfo=datetime.timezone.utc)


def _run(
    name: str = "backup",
    status: JobStatus = JobStatus.FAILURE,
    start_hour: int = 12,
    end_hour: int = 12,
    tags: List[str] | None = None,
) -> JobRun:
    run = JobRun(job_name=name)
    run.start_time = _utc(start_hour)
    run.end_time = _utc(end_hour)
    run.status = status
    run.tags = tags or []
    return run


@pytest.fixture()
def suppressor() -> Suppressor:
    return Suppressor()


# --- is_suppressed -----------------------------------------------------------

def test_no_rules_never_suppressed(suppressor):
    run = _run()
    assert suppressor.is_suppressed(run) is None


def test_rule_matches_by_job_name(suppressor):
    rule = SuppressionRule(name="r1", job_names=["backup"])
    suppressor.add_rule(rule)
    assert suppressor.is_suppressed(_run(name="backup")) is rule


def test_rule_does_not_match_different_job(suppressor):
    rule = SuppressionRule(name="r1", job_names=["backup"])
    suppressor.add_rule(rule)
    assert suppressor.is_suppressed(_run(name="cleanup")) is None


def test_rule_matches_by_status(suppressor):
    rule = SuppressionRule(name="r2", statuses=[JobStatus.FAILURE])
    suppressor.add_rule(rule)
    assert suppressor.is_suppressed(_run(status=JobStatus.FAILURE)) is rule
    assert suppressor.is_suppressed(_run(status=JobStatus.SUCCESS)) is None


def test_rule_matches_by_max_duration(suppressor):
    rule = SuppressionRule(name="r3", max_duration=0.0)
    suppressor.add_rule(rule)
    # start == end → duration 0 → suppressed
    assert suppressor.is_suppressed(_run(start_hour=12, end_hour=12)) is rule


def test_rule_not_matched_when_duration_exceeds_max(suppressor):
    rule = SuppressionRule(name="r3", max_duration=0.0)
    suppressor.add_rule(rule)
    run = _run(start_hour=11, end_hour=12)  # 3600 s
    assert suppressor.is_suppressed(run) is None


def test_rule_matches_tags(suppressor):
    rule = SuppressionRule(name="r4", tags=["nightly"])
    suppressor.add_rule(rule)
    assert suppressor.is_suppressed(_run(tags=["nightly", "prod"])) is rule
    assert suppressor.is_suppressed(_run(tags=["prod"])) is None


def test_first_matching_rule_returned(suppressor):
    r1 = SuppressionRule(name="r1", job_names=["backup"])
    r2 = SuppressionRule(name="r2", job_names=["backup"])
    suppressor.add_rule(r1)
    suppressor.add_rule(r2)
    assert suppressor.is_suppressed(_run(name="backup")) is r1


# --- filter_runs -------------------------------------------------------------

def test_filter_runs_removes_suppressed(suppressor):
    rule = SuppressionRule(name="r1", job_names=["backup"])
    suppressor.add_rule(rule)
    runs = [_run(name="backup"), _run(name="cleanup")]
    kept = suppressor.filter_runs(runs)
    assert len(kept) == 1
    assert kept[0].job_name == "cleanup"


def test_filter_runs_calls_callback_for_suppressed(suppressor):
    rule = SuppressionRule(name="r1", job_names=["backup"])
    suppressor.add_rule(rule)
    suppressed_log = []
    suppressor.filter_runs(
        [_run(name="backup")],
        on_suppressed=lambda run, r: suppressed_log.append((run.job_name, r.name)),
    )
    assert suppressed_log == [("backup", "r1")]


def test_rules_property_returns_copy(suppressor):
    rule = SuppressionRule(name="r1")
    suppressor.add_rule(rule)
    rules = suppressor.rules
    rules.clear()
    assert len(suppressor.rules) == 1
