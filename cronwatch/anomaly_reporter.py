"""Format anomaly records for CLI display."""
from __future__ import annotations

from typing import List

from cronwatch.anomaly import AnomalyRecord

_COL = (
    ("Job", 24),
    ("First Seen", 20),
    ("Last Seen", 20),
    ("Count", 7),
    ("Suppressed", 11),
)

_DT_FMT = "%Y-%m-%d %H:%M:%S"


def _header() -> str:
    return "  ".join(name.ljust(w) for name, w in _COL)


def _sep() -> str:
    return "  ".join("-" * w for _, w in _COL)


def _row(rec: AnomalyRecord) -> str:
    cols = [
        rec.job_name[:24].ljust(24),
        rec.first_seen.strftime(_DT_FMT).ljust(20),
        rec.last_seen.strftime(_DT_FMT).ljust(20),
        str(rec.count).ljust(7),
        str(rec.suppressed).ljust(11),
    ]
    return "  ".join(cols)


def format_anomaly_table(records: List[AnomalyRecord]) -> str:
    """Return a formatted table of anomaly records sorted by last seen (newest first)."""
    if not records:
        return "No active anomalies."
    lines = [_header(), _sep()]
    for rec in sorted(records, key=lambda r: r.last_seen, reverse=True):
        lines.append(_row(rec))
    return "\n".join(lines)


def format_anomaly_summary(records: List[AnomalyRecord]) -> str:
    """Return a one-line summary of the anomaly records.

    Example: "3 anomalies across 2 jobs (5 suppressed)"
    """
    if not records:
        return "No active anomalies."
    total_count = sum(r.count for r in records)
    total_suppressed = sum(r.suppressed for r in records)
    job_count = len({r.job_name for r in records})
    return (
        f"{total_count} anomaly occurrence(s) across {job_count} job(s) "
        f"({total_suppressed} suppressed)"
    )
