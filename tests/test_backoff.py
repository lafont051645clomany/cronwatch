"""Tests for cronwatch.backoff."""
import pytest
from cronwatch.backoff import BackoffConfig, BackoffTracker


T0 = 1_000.0  # arbitrary monotonic epoch


@pytest.fixture()
def cfg() -> BackoffConfig:
    return BackoffConfig(base_seconds=60.0, max_seconds=480.0, multiplier=2.0)


@pytest.fixture()
def tracker(cfg: BackoffConfig) -> BackoffTracker:
    return BackoffTracker(cfg)


# ---------------------------------------------------------------------------
# is_suppressed
# ---------------------------------------------------------------------------

def test_first_alert_not_suppressed(tracker: BackoffTracker) -> None:
    assert tracker.is_suppressed("job_a", now=T0) is False


def test_after_record_within_window_is_suppressed(tracker: BackoffTracker) -> None:
    tracker.record("job_a", now=T0)
    # 30 s later – still inside the 60 s base window
    assert tracker.is_suppressed("job_a", now=T0 + 30) is True


def test_after_record_window_expires_not_suppressed(tracker: BackoffTracker) -> None:
    tracker.record("job_a", now=T0)
    # 61 s later – window has elapsed
    assert tracker.is_suppressed("job_a", now=T0 + 61) is False


# ---------------------------------------------------------------------------
# record / window growth
# ---------------------------------------------------------------------------

def test_first_record_returns_base_window(tracker: BackoffTracker) -> None:
    window = tracker.record("job_a", now=T0)
    assert window == 60.0


def test_second_record_doubles_window(tracker: BackoffTracker) -> None:
    tracker.record("job_a", now=T0)
    window = tracker.record("job_a", now=T0 + 120)
    assert window == 120.0


def test_window_capped_at_max(tracker: BackoffTracker) -> None:
    t = T0
    window = 0.0
    for _ in range(10):  # 60 → 120 → 240 → 480 → capped
        window = tracker.record("job_a", now=t)
        t += window + 1
    assert window == 480.0


def test_count_increments_with_each_record(tracker: BackoffTracker) -> None:
    tracker.record("job_a", now=T0)
    tracker.record("job_a", now=T0 + 200)
    state = tracker.state("job_a")
    assert state is not None
    assert state.count == 2


# ---------------------------------------------------------------------------
# reset
# ---------------------------------------------------------------------------

def test_reset_clears_suppression(tracker: BackoffTracker) -> None:
    tracker.record("job_a", now=T0)
    tracker.reset("job_a")
    assert tracker.is_suppressed("job_a", now=T0 + 1) is False


def test_reset_unknown_job_is_noop(tracker: BackoffTracker) -> None:
    tracker.reset("ghost")  # must not raise


def test_after_reset_window_restarts_from_base(tracker: BackoffTracker) -> None:
    tracker.record("job_a", now=T0)
    tracker.record("job_a", now=T0 + 200)  # window now 120 s
    tracker.reset("job_a")
    window = tracker.record("job_a", now=T0 + 400)
    assert window == 60.0  # back to base


# ---------------------------------------------------------------------------
# jobs()
# ---------------------------------------------------------------------------

def test_jobs_returns_tracked_names(tracker: BackoffTracker) -> None:
    tracker.record("alpha", now=T0)
    tracker.record("beta", now=T0)
    assert set(tracker.jobs()) == {"alpha", "beta"}


def test_jobs_empty_initially(tracker: BackoffTracker) -> None:
    assert tracker.jobs() == []
