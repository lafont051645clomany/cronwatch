"""Render ForecastResult objects as a CLI table."""
from __future__ import annotations

from typing import List

from cronwatch.forecast import ForecastResult

_NA = "n/a"


def _pct(v: float | None) -> str:
    if v is None:
        return _NA
    return f"{v * 100:.1f}%"


def _slope(v: float | None) -> str:
    if v is None:
        return _NA
    sign = "+" if v >= 0 else ""
    return f"{sign}{v * 100:.2f}%/h"


def _trend_arrow(result: ForecastResult) -> str:
    if result.slope_per_hour is None:
        return "?"
    if result.slope_per_hour > 0.005:
        return "↑"
    if result.slope_per_hour < -0.005:
        return "↓"
    return "→"


_HEADER = (
    f"{'Job':<24} {'Samples':>7} {'Cur%':>6} {'Slope':>10}"
    f" {'1h%':>6} {'24h%':>6} {'Conf':<8} {'Trend':>5}"
)
_SEP = "-" * len(_HEADER)


def _row(r: ForecastResult) -> str:
    return (
        f"{r.job_name:<24} {r.samples:>7} {_pct(r.current_fail_rate):>6}"
        f" {_slope(r.slope_per_hour):>10} {_pct(r.predicted_fail_rate_1h):>6}"
        f" {_pct(r.predicted_fail_rate_24h):>6} {r.confidence:<8} {_trend_arrow(r):>5}"
    )


def format_forecast_table(results: List[ForecastResult]) -> str:
    if not results:
        return "No forecast data available."
    lines = [_HEADER, _SEP]
    lines.extend(_row(r) for r in results)
    return "\n".join(lines)
