"""Formatting helpers for PagerDuty delivery results."""
from __future__ import annotations

from typing import Sequence

from cronwatch.notifier import NotificationResult

_COL_CHANNEL = 12
_COL_SUCCESS = 8
_COL_DETAIL = 30


def _header() -> str:
    return (
        f"{'Channel':<{_COL_CHANNEL}}  "
        f"{'Success':<{_COL_SUCCESS}}  "
        f"{'Detail':<{_COL_DETAIL}}"
    )


def _sep() -> str:
    return "-" * (_COL_CHANNEL + _COL_SUCCESS + _COL_DETAIL + 4)


def _row(result: NotificationResult) -> str:
    success_str = "yes" if result.success else "no"
    detail = result.detail or result.error or ""
    if len(detail) > _COL_DETAIL:
        detail = detail[: _COL_DETAIL - 1] + "…"
    return (
        f"{result.channel:<{_COL_CHANNEL}}  "
        f"{success_str:<{_COL_SUCCESS}}  "
        f"{detail:<{_COL_DETAIL}}"
    )


def format_pagerduty_results(results: Sequence[NotificationResult]) -> str:
    """Return a plain-text table summarising PagerDuty delivery results."""
    if not results:
        return "No PagerDuty delivery results."

    lines = [_header(), _sep()]
    for r in results:
        lines.append(_row(r))

    ok = sum(1 for r in results if r.success)
    lines.append(_sep())
    lines.append(f"Delivered: {ok}/{len(results)}")
    return "\n".join(lines)
