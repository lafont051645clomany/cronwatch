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


def _header() -> str:
    return "  ".join(name.ljust(w) for name, w in _COL)


def _sep() -> str:
    return "  ".join("-" * w for _, w in _COL)


def _row(rec: AnomalyRecord) -> str:
    cols = [
        rec.job_name[:24].ljust(24),
        rec.first_seen.strftime("%Y-%m-%d %H:%M:%S").ljust(20),
        rec.last_seen.strftime("%Y-%m-%d %H:%M:%S").ljust(20),
        str(rec.count).ljust(7),
        str(rec.suppressed).ljust(11),
    ]
    return "  ".join(cols)


def format_anomaly_table(records: List[AnomalyRecord]) -> str:
    if not records:
        return "No active anomalies."
    lines = [_header(), _sep()]
    for rec in sorted(records, key=lambda r: r.last_seen, reverse=True):
        lines.append(_row(rec))
    return "\n".join(lines)
