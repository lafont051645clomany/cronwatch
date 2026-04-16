"""Format trend analysis results for CLI output."""
from __future__ import annotations
from typing import List
from cronwatch.trend import TrendResult

_ARROWS = {
    'improving': '\u2193',
    'degrading': '\u2191',
    'stable': '\u2192',
    'insufficient': '?',
}


def _fmt_slope(slope) -> str:
    if slope is None:
        return 'n/a'
    sign = '+' if slope >= 0 else ''
    return f'{sign}{slope:.2f}s/run'


def _fmt_delta(delta) -> str:
    if delta is None:
        return 'n/a'
    sign = '+' if delta >= 0 else ''
    return f'{sign}{delta*100:.1f}%'


def format_trend_table(results: List[TrendResult]) -> str:
    if not results:
        return 'No trend data available.'

    header = f"{'Job':<30} {'Dir':<12} {'Slope':<14} {'Fail\u0394':<10} {'N':>5}"
    sep = '-' * len(header)
    rows = [header, sep]
    for r in results:
        arrow = _ARROWS.get(r.direction, '?')
        rows.append(
            f"{r.job_name:<30} {arrow+' '+r.direction:<12} "
            f"{_fmt_slope(r.slope):<14} {_fmt_delta(r.failure_rate_delta):<10} {r.sample_count:>5}"
        )
    return '\n'.join(rows)
