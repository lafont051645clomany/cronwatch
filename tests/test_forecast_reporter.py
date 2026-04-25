"""Tests for cronwatch.forecast_reporter."""
from __future__ import annotations

from cronwatch.forecast import ForecastResult
from cronwatch.forecast_reporter import (
    format_forecast_table,
    _pct,
    _slope,
    _trend_arrow,
)


def _result(
    job: str = "my_job",
    samples: int = 10,
    current: float = 0.25,
    slope: float | None = 0.01,
    pred_1h: float | None = 0.26,
    pred_24h: float | None = 0.49,
    confidence: str = "medium",
) -> ForecastResult:
    return ForecastResult(
        job_name=job,
        samples=samples,
        current_fail_rate=current,
        slope_per_hour=slope,
        predicted_fail_rate_1h=pred_1h,
        predicted_fail_rate_24h=pred_24h,
        confidence=confidence,
    )


# --- helpers ---

def test_pct_formats_percentage():
    assert _pct(0.5) == "50.0%"


def test_pct_none_returns_na():
    assert _pct(None) == "n/a"


def test_slope_positive_has_plus_sign():
    assert "+" in _slope(0.01)


def test_slope_negative_has_minus():
    assert "-" in _slope(-0.02)


def test_slope_none_returns_na():
    assert _slope(None) == "n/a"


def test_trend_arrow_up_when_degrading():
    r = _result(slope=0.05)
    assert _trend_arrow(r) == "↑"


def test_trend_arrow_down_when_improving():
    r = _result(slope=-0.05)
    assert _trend_arrow(r) == "↓"


def test_trend_arrow_flat():
    r = _result(slope=0.001)
    assert _trend_arrow(r) == "→"


def test_trend_arrow_unknown_when_no_slope():
    r = _result(slope=None)
    assert _trend_arrow(r) == "?"


# --- format_forecast_table ---

def test_empty_returns_message():
    assert "No forecast" in format_forecast_table([])


def test_table_contains_job_name():
    table = format_forecast_table([_result(job="backup_job")])
    assert "backup_job" in table


def test_table_contains_confidence():
    table = format_forecast_table([_result(confidence="high")])
    assert "high" in table


def test_table_contains_sample_count():
    table = format_forecast_table([_result(samples=42)])
    assert "42" in table


def test_table_multiple_rows():
    results = [_result(job="job_a"), _result(job="job_b")]
    table = format_forecast_table(results)
    assert "job_a" in table
    assert "job_b" in table
