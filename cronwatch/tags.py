"""Tag-based filtering and grouping for cron job runs."""
from __future__ import annotations

from typing import Dict, Iterable, List

from cronwatch.tracker import JobRun


def runs_with_tag(runs: Iterable[JobRun], tag: str) -> List[JobRun]:
    """Return runs whose job name carries the given tag.

    Tags are stored in ``JobRun.tags`` — a plain list of strings attached
    to a run at ping/finish time.  If a run has no ``tags`` attribute the
    run is skipped silently so the helper works with older run objects.
    """
    tag_lower = tag.lower()
    result: List[JobRun] = []
    for run in runs:
        run_tags = getattr(run, "tags", None) or []
        if any(t.lower() == tag_lower for t in run_tags):
            result.append(run)
    return result


def group_by_tag(runs: Iterable[JobRun]) -> Dict[str, List[JobRun]]:
    """Partition *runs* into a mapping of tag → [run, …].

    A run that carries multiple tags appears under each of them.  Runs
    without tags are collected under the empty-string key ``""``.
    """
    groups: Dict[str, List[JobRun]] = {}
    for run in runs:
        run_tags = getattr(run, "tags", None) or []
        if not run_tags:
            groups.setdefault("", []).append(run)
        else:
            for tag in run_tags:
                groups.setdefault(tag, []).append(run)
    return groups


def all_tags(runs: Iterable[JobRun]) -> List[str]:
    """Return a sorted, deduplicated list of every tag seen across *runs*."""
    seen: set[str] = set()
    for run in runs:
        for tag in getattr(run, "tags", None) or []:
            seen.add(tag)
    return sorted(seen)
