"""Text-based heatmap reporter for cronwatch."""
from __future__ import annotations

from typing import List

from cronwatch.heatmap import DAYS, HOURS, Heatmap

_DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _shade(rate: float | None) -> str:
    """Return a single character representing failure rate."""
    if rate is None:
        return "."
    if rate == 0.0:
        return " "
    if rate < 0.25:
        return "░"
    if rate < 0.50:
        return "▒"
    if rate < 0.75:
        return "▓"
    return "█"


def format_heatmap(hm: Heatmap) -> str:
    """Render a 7-row × 24-column failure-rate heatmap as a string."""
    hour_header = "     " + "".join(f"{h:2d}" for h in HOURS)
    lines: List[str] = [
        f"Heatmap: {hm.job}  (. = no data, ' ' = 0 %, ░<25 %, ▒<50 %, ▓<75 %, █≥75 %)",
        hour_header,
        "     " + "--" * 24,
    ]
    for day in DAYS:
        row = f"{_DAY_LABELS[day]}  |"
        for hour in HOURS:
            cell = hm.get(day, hour)
            row += f" {_shade(cell.failure_rate)}"
        lines.append(row)
    return "\n".join(lines)


def format_heatmap_counts(hm: Heatmap) -> str:
    """Render a 7-row × 24-column total-run-count heatmap."""
    hour_header = "     " + "".join(f"{h:2d}" for h in HOURS)
    lines: List[str] = [
        f"Run counts: {hm.job}",
        hour_header,
        "     " + "--" * 24,
    ]
    for day in DAYS:
        row = f"{_DAY_LABELS[day]}  |"
        for hour in HOURS:
            total = hm.get(day, hour).total
            row += f"{total:2d}" if total else "  "
        lines.append(row)
    return "\n".join(lines)
