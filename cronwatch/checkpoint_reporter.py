"""Format checkpoint data for CLI display."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict

_HDR = ("Job", "Last Success", "Age")
_COL = (30, 26, 18)


def _fmt_dt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S %Z")


def _fmt_age(dt: datetime) -> str:
    delta = datetime.now(tz=timezone.utc) - dt
    total = int(delta.total_seconds())
    if total < 60:
        return f"{total}s ago"
    if total < 3600:
        return f"{total // 60}m ago"
    if total < 86400:
        return f"{total // 3600}h ago"
    return f"{total // 86400}d ago"


def _sep() -> str:
    return "-+-".join("-" * w for w in _COL)


def _row(*cells: str) -> str:
    return " | ".join(str(c).ljust(w) for c, w in zip(cells, _COL))


def format_checkpoint_table(checkpoints: Dict[str, datetime]) -> str:
    if not checkpoints:
        return "No checkpoints recorded."

    lines = [
        _row(*_HDR),
        _sep(),
    ]
    for name, dt in sorted(checkpoints.items()):
        lines.append(_row(name, _fmt_dt(dt), _fmt_age(dt)))
    return "\n".join(lines)
