"""Tests for cronwatch.trend_reporter."""
from cronwatch.trend import TrendResult
from cronwatch.trend_reporter import format_trend_table, _fmt_slope, _fmt_delta


def test_fmt_slope_positive():
    assert _fmt_slope(2.5) == '+2.50s/run'


def test_fmt_slope_negative():
    assert _fmt_slope(-1.0) == '-1.00s/run'


def test_fmt_slope_none():
    assert _fmt_slope(None) == 'n/a'


def test_fmt_delta_positive():
    assert _fmt_delta(0.15) == '+15.0%'


def test_fmt_delta_none():
    assert _fmt_delta(None) == 'n/a'


def test_format_empty():
    assert format_trend_table([]) == 'No trend data available.'


def test_format_table_contains_job_name():
    r = TrendResult('backup', 10, 'stable', 0.1, 0.0)
    out = format_trend_table([r])
    assert 'backup' in out
    assert 'stable' in out


def test_format_table_degrading_arrow():
    r = TrendResult('sync', 8, 'degrading', 3.5, 0.2)
    out = format_trend_table([r])
    assert '↑' in out


def test_format_table_improving_arrow():
    r = TrendResult('etl', 6, 'improving', -2.0, -0.15)
    out = format_trend_table([r])
    assert '↓' in out


def test_format_table_insufficient():
    r = TrendResult('new_job', 2, 'insufficient', None, None)
    out = format_trend_table([r])
    assert 'insufficient' in out
    assert 'n/a' in out
