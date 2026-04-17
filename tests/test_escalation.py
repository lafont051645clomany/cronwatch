"""Tests for cronwatch.escalation."""
import pytest
from datetime import datetime
from cronwatch.escalation import EscalationPolicy, EscalationTracker


@pytest.fixture
def policy():
    return EscalationPolicy(threshold=3, escalation_emails=["ops@example.com"])


@pytest.fixture
def tracker(policy):
    return EscalationTracker(policy)


def test_initial_state_is_none(tracker):
    assert tracker.get_state("backup") is None


def test_single_failure_not_escalated(tracker):
    state = tracker.record_failure("backup")
    assert state.consecutive_failures == 1
    assert not state.is_escalated


def test_escalates_at_threshold(tracker):
    for _ in range(3):
        state = tracker.record_failure("backup")
    assert state.is_escalated
    assert state.escalated_at is not None


def test_does_not_re_escalate_after_threshold(tracker):
    for _ in range(5):
        state = tracker.record_failure("backup")
    assert state.consecutive_failures == 5
    # escalated_at should be set only once (at threshold)
    assert state.is_escalated


def test_success_resolves_escalation(tracker):
    for _ in range(3):
        tracker.record_failure("backup")
    state = tracker.record_success("backup")
    assert not state.is_escalated
    assert state.resolved_at is not None
    assert state.consecutive_failures == 0


def test_success_without_escalation_resets_count(tracker):
    tracker.record_failure("backup")
    state = tracker.record_success("backup")
    assert state.consecutive_failures == 0
    assert state.resolved_at is None


def test_all_escalated_returns_only_active(tracker):
    tracker.record_failure("job_a")
    tracker.record_failure("job_a")
    tracker.record_failure("job_a")  # escalated
    tracker.record_failure("job_b")  # not yet escalated
    escalated = tracker.all_escalated()
    assert len(escalated) == 1
    assert escalated[0].job_name == "job_a"


def test_escalation_timestamp_recorded(tracker):
    t = datetime(2024, 1, 15, 12, 0, 0)
    for _ in range(3):
        state = tracker.record_failure("backup", now=t)
    assert state.escalated_at == t
