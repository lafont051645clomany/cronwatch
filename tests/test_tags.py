"""Tests for cronwatch.tags."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

import pytest

from cronwatch.tracker import JobRun, JobStatus
from cronwatch.tags import all_tags, group_by_tag, runs_with_tag


def _run(
    job: str = "backup",
    status: JobStatus = JobStatus.SUCCESS,
    tags: Optional[List[str]] = None,
) -> JobRun:
    now = datetime.now(timezone.utc)
    run = JobRun(job_name=job, started_at=now, status=status)
    run.tags = tags or []
    return run


@pytest.fixture()
def mixed_runs():
    return [
        _run("backup", tags=["nightly", "critical"]),
        _run("cleanup", tags=["nightly"]),
        _run("report", tags=["daily"]),
        _run("ping", tags=[]),
    ]


# ---------------------------------------------------------------------------
# runs_with_tag
# ---------------------------------------------------------------------------

def test_runs_with_tag_returns_matching(mixed_runs):
    result = runs_with_tag(mixed_runs, "nightly")
    assert len(result) == 2
    names = {r.job_name for r in result}
    assert names == {"backup", "cleanup"}


def test_runs_with_tag_case_insensitive(mixed_runs):
    result = runs_with_tag(mixed_runs, "NIGHTLY")
    assert len(result) == 2


def test_runs_with_tag_no_match_returns_empty(mixed_runs):
    assert runs_with_tag(mixed_runs, "unknown") == []


def test_runs_with_tag_tolerates_missing_attribute():
    run = JobRun(job_name="x", started_at=datetime.now(timezone.utc), status=JobStatus.SUCCESS)
    # no .tags attribute set
    assert runs_with_tag([run], "nightly") == []


# ---------------------------------------------------------------------------
# group_by_tag
# ---------------------------------------------------------------------------

def test_group_by_tag_keys(mixed_runs):
    groups = group_by_tag(mixed_runs)
    assert "nightly" in groups
    assert "critical" in groups
    assert "daily" in groups
    assert "" in groups  # the untagged ping run


def test_group_by_tag_multi_tag_run_appears_in_both(mixed_runs):
    groups = group_by_tag(mixed_runs)
    nightly_names = {r.job_name for r in groups["nightly"]}
    critical_names = {r.job_name for r in groups["critical"]}
    assert "backup" in nightly_names
    assert "backup" in critical_names


def test_group_by_tag_untagged_under_empty_key(mixed_runs):
    groups = group_by_tag(mixed_runs)
    assert any(r.job_name == "ping" for r in groups[""])


# ---------------------------------------------------------------------------
# all_tags
# ---------------------------------------------------------------------------

def test_all_tags_sorted_and_unique(mixed_runs):
    tags = all_tags(mixed_runs)
    assert tags == sorted(set(tags))
    assert "nightly" in tags
    assert "critical" in tags
    assert "daily" in tags


def test_all_tags_empty_when_no_runs():
    assert all_tags([]) == []


def test_all_tags_excludes_empty_string(mixed_runs):
    """The empty-string sentinel used in group_by_tag must not appear here."""
    tags = all_tags(mixed_runs)
    assert "" not in tags
