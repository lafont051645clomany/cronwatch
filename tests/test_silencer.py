"""Tests for cronwatch.silencer."""
from datetime import datetime, timedelta
import pytest

from cronwatch.silencer import Silencer, SilenceWindow

NOW = datetime(2024, 6, 1, 12, 0, 0)
PAST = NOW - timedelta(hours=2)
FUTURE = NOW + timedelta(hours=2)


@pytest.fixture
def silencer():
    return Silencer()


def _window(job: str, start=None, end=None, reason="maint") -> SilenceWindow:
    return SilenceWindow(
        job_name=job,
        start=start or (NOW - timedelta(hours=1)),
        end=end or (NOW + timedelta(hours=1)),
        reason=reason,
    )


def test_is_active_within_window():
    w = _window("backup")
    assert w.is_active(NOW) is True


def test_is_active_before_window():
    w = _window("backup", start=NOW + timedelta(minutes=1))
    assert w.is_active(NOW) is False


def test_is_active_after_window():
    w = _window("backup", end=NOW - timedelta(minutes=1))
    assert w.is_active(NOW) is False


def test_silenced_when_active_window(silencer):
    silencer.add(_window("backup"))
    assert silencer.is_silenced("backup", at=NOW) is True


def test_not_silenced_when_no_window(silencer):
    assert silencer.is_silenced("backup", at=NOW) is False


def test_not_silenced_different_job(silencer):
    silencer.add(_window("backup"))
    assert silencer.is_silenced("cleanup", at=NOW) is False


def test_active_windows_returns_only_active(silencer):
    silencer.add(_window("backup"))
    silencer.add(_window("cleanup", start=NOW + timedelta(hours=1)))
    active = silencer.active_windows(at=NOW)
    assert len(active) == 1
    assert active[0].job_name == "backup"


def test_remove_existing_window(silencer):
    start = NOW - timedelta(hours=1)
    silencer.add(_window("backup", start=start))
    removed = silencer.remove("backup", start)
    assert removed is True
    assert silencer.is_silenced("backup", at=NOW) is False


def test_remove_nonexistent_returns_false(silencer):
    assert silencer.remove("ghost", NOW) is False


def test_purge_expired_removes_old(silencer):
    silencer.add(_window("backup", end=NOW - timedelta(seconds=1)))
    silencer.add(_window("cleanup"))
    purged = silencer.purge_expired(at=NOW)
    assert purged == 1
    assert len(silencer.all_windows()) == 1


def test_all_windows_returns_everything(silencer):
    silencer.add(_window("a"))
    silencer.add(_window("b"))
    assert len(silencer.all_windows()) == 2
