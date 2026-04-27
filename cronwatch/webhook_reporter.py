"""Format webhook delivery results for CLI display."""
from __future__ import annotations

from cronwatch.webhook import WebhookResult

_HEADER = ("URL", "Status", "OK", "Error")
_WIDTHS = (40, 8, 6, 30)


def _sep() -> str:
    return "+" + "+".join("-" * (w + 2) for w in _WIDTHS) + "+"


def _row(*cells: str) -> str:
    parts = [
        f" {str(c)[:w]:<{w}} " for c, w in zip(cells, _WIDTHS)
    ]
    return "|" + "|".join(parts) + "|"


def format_webhook_results(results: list[WebhookResult]) -> str:
    """Return a formatted table of webhook delivery results."""
    if not results:
        return "No webhook deliveries recorded."

    sep = _sep()
    lines = [sep, _row(*_HEADER), sep]
    for r in results:
        status = str(r.status_code) if r.status_code is not None else "—"
        ok = "yes" if r.success else "no"
        error = r.error or ""
        lines.append(_row(r.url, status, ok, error))
    lines.append(sep)
    return "\n".join(lines)
