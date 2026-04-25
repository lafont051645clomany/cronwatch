"""Format ReplayResult lists as human-readable tables."""
from __future__ import annotations

from typing import List

from cronwatch.replay import ReplayResult

_COL_ID = 36
_COL_JOB = 20
_COL_STATUS = 10
_COL_DISPATCHED = 10
_COL_NOTES = 40


def _header() -> str:
    return (
        f"{'Run ID':<{_COL_ID}}  "
        f"{'Job':<{_COL_JOB}}  "
        f"{'Status':<{_COL_STATUS}}  "
        f"{'Dispatched':<{_COL_DISPATCHED}}  "
        f"Notes"
    )


def _sep() -> str:
    return "-" * (_COL_ID + _COL_JOB + _COL_STATUS + _COL_DISPATCHED + _COL_NOTES + 8)


def _row(result: ReplayResult) -> str:
    run = result.run
    notes_str = "; ".join(result.notes) if result.notes else ""
    return (
        f"{run.run_id:<{_COL_ID}}  "
        f"{run.job_name:<{_COL_JOB}}  "
        f"{run.status.value:<{_COL_STATUS}}  "
        f"{'yes' if result.dispatched else 'no':<{_COL_DISPATCHED}}  "
        f"{notes_str}"
    )


def format_replay_table(results: List[ReplayResult]) -> str:
    """Return a formatted table of *results*, or a short message when empty."""
    if not results:
        return "No replay results to display."

    lines = [_header(), _sep()]
    lines.extend(_row(r) for r in results)

    dispatched = sum(1 for r in results if r.dispatched)
    lines.append(_sep())
    lines.append(f"Total: {len(results)}  Dispatched: {dispatched}  Suppressed: {len(results) - dispatched}")
    return "\n".join(lines)
