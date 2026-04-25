"""Format retention results and config for CLI display."""
from __future__ import annotations

from typing import List

from cronwatch.retention import RetentionConfig, RetentionResult

_COL = 24


def _header() -> str:
    return (
        f"{'Policy':<{_COL}}  {'Value'}"
        "\n" + "-" * (_COL + 18)
    )


def format_retention_config(cfg: RetentionConfig) -> str:
    """Render a human-readable table of the active retention policy."""
    rows = [
        ("Max age (days)", str(cfg.max_age_days) if cfg.max_age_days is not None else "unlimited"),
        ("Max runs / job", str(cfg.max_runs_per_job) if cfg.max_runs_per_job is not None else "unlimited"),
        ("Keep failures", "yes" if cfg.keep_failures else "no"),
    ]
    lines = [_header()]
    for label, value in rows:
        lines.append(f"{label:<{_COL}}  {value}")
    return "\n".join(lines)


def format_retention_result(result: RetentionResult) -> str:
    """Render a summary table after a retention pass."""
    rows = [
        ("Runs before", str(result.total_before)),
        ("Runs after", str(result.total_after)),
        ("Dropped", str(result.dropped)),
        ("Failure-protected", str(result.kept_due_to_failure)),
    ]
    lines = [_header()]
    for label, value in rows:
        lines.append(f"{label:<{_COL}}  {value}")
    return "\n".join(lines)


def format_retention_results(results: List[RetentionResult]) -> str:
    """Summarise multiple retention results (e.g. across several history files)."""
    if not results:
        return "No retention results to display."
    total_before = sum(r.total_before for r in results)
    total_after = sum(r.total_after for r in results)
    dropped = sum(r.dropped for r in results)
    protected = sum(r.kept_due_to_failure for r in results)
    from cronwatch.retention import RetentionResult as RR
    combined = RR(
        total_before=total_before,
        total_after=total_after,
        dropped=dropped,
        kept_due_to_failure=protected,
    )
    return format_retention_result(combined)
