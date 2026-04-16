"""Tests for cronwatch.anomaly_reporter."""
from datetime import datetime

from cronwatch.anomaly import AnomalyRecord
from cronwatch.anomaly_reporter import format_anomaly_table


def _rec(
    name: str = "backup",
    count: int = 2,
    suppressed: int = 0,
    first: datetime = datetime(2024, 1, 1, 10, 0, 0),
    last: datetime = datetime(2024, 1, 1, 11, 0, 0),
) -> AnomalyRecord:
    return AnomalyRecord(
        job_name=name,
        first_seen=first,
        last_seen=last,
        count=count,
        suppressed=suppressed,
    )


def test_empty_returns_message():
    assert format_anomaly_table([]) == "No active anomalies."


def test_table_contains_job_name():
    out = format_anomaly_table([_rec("my_job")])
    assert "my_job" in out


def test_table_contains_count():
    out = format_anomaly_table([_rec(count=5)])
    assert "5" in out


def test_table_contains_suppressed():
    out = format_anomaly_table([_rec(suppressed=3)])
    assert "3" in out


def test_table_has_header():
    out = format_anomaly_table([_rec()])
    assert "Job" in out
    assert "Count" in out
    assert "Suppressed" in out


def test_multiple_records_sorted_by_last_seen():
    r1 = _rec("early", last=datetime(2024, 1, 1, 9, 0, 0))
    r2 = _rec("late", last=datetime(2024, 1, 1, 12, 0, 0))
    out = format_anomaly_table([r1, r2])
    assert out.index("late") < out.index("early")


def test_long_job_name_truncated():
    name = "a" * 40
    out = format_anomaly_table([_rec(name=name)])
    assert "a" * 24 in out
    assert "a" * 25 not in out
