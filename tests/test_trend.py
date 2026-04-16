"""Tests for cronwatch.trend."""
from datetime import datetime, timedelta
import pytest
from cronwatch.tracker import JobRun, JobStatus
from cronwatch.trend import analyse_trend, _linear_slope


def _run(job, offset_minutes, duration, status=JobStatus.SUCCESS):
    start = datetime(2024, 1, 1, 0, 0) + timedelta(minutes=offset_minutes)
    end = start + timedelta(seconds=duration)
    return JobRun(job_name=job, run_id=f'r{offset_minutes}',
                  started_at=start, finished_at=end, status=status)


def test_linear_slope_flat():
    assert _linear_slope([5.0, 5.0, 5.0, 5.0, 5.0]) == pytest.approx(0.0)


def test_linear_slope_increasing():
    slope = _linear_slope([1.0, 2.0, 3.0, 4.0, 5.0])
    assert slope > 0


def test_linear_slope_decreasing():
    slope = _linear_slope([5.0, 4.0, 3.0, 2.0, 1.0])
    assert slope < 0


def test_insufficient_samples():
    runs = [_run('job1', i * 10, 30) for i in range(3)]
    result = analyse_trend(runs, 'job1', min_samples=5)
    assert result.direction == 'insufficient'
    assert result.slope is None


def test_stable_trend():
    runs = [_run('job1', i * 10, 30) for i in range(10)]
    result = analyse_trend(runs, 'job1', min_samples=5, slope_threshold=1.0)
    assert result.direction == 'stable'
    assert result.sample_count == 10


def test_degrading_duration():
    # durations increase by 5s each run -> slope >> threshold
    runs = [_run('job1', i * 10, i * 5 + 10) for i in range(10)]
    result = analyse_trend(runs, 'job1', min_samples=5, slope_threshold=1.0)
    assert result.direction == 'degrading'
    assert result.slope > 1.0


def test_improving_duration():
    runs = [_run('job1', i * 10, max(1, 60 - i * 5)) for i in range(10)]
    result = analyse_trend(runs, 'job1', min_samples=5, slope_threshold=1.0)
    assert result.direction == 'improving'


def test_filters_by_job_name():
    runs = (
        [_run('job1', i * 10, 30) for i in range(10)] +
        [_run('job2', i * 10, 30) for i in range(10)]
    )
    result = analyse_trend(runs, 'job1')
    assert result.job_name == 'job1'
    assert result.sample_count == 10
