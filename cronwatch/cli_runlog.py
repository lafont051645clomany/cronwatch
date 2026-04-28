"""CLI subcommand for browsing and filtering the structured run log."""

from __future__ import annotations

import argparse
from pathlib import Path

from cronwatch.runlog import RunLog
from cronwatch.runlog_reporter import format_runlog_table, format_runlog_summary


def add_runlog_subparser(subparsers: argparse._SubParsersAction) -> None:  # noqa: SLF001
    """Register the ``runlog`` subcommand on *subparsers*."""
    p = subparsers.add_parser(
        "runlog",
        help="Browse structured run-log entries.",
        description=(
            "Display and filter entries from the cronwatch run log. "
            "Entries can be narrowed by job name, status, or a maximum entry count."
        ),
    )
    p.add_argument(
        "--log",
        metavar="PATH",
        default="cronwatch_runlog.jsonl",
        help="Path to the run-log file (default: cronwatch_runlog.jsonl).",
    )
    p.add_argument(
        "--job",
        metavar="NAME",
        default=None,
        help="Filter entries to a specific job name (case-insensitive).",
    )
    p.add_argument(
        "--status",
        metavar="STATUS",
        choices=["success", "failure", "timeout", "unknown"],
        default=None,
        help="Filter entries by run status.",
    )
    p.add_argument(
        "--last",
        metavar="N",
        type=int,
        default=None,
        help="Show only the N most recent entries.",
    )
    p.add_argument(
        "--summary",
        action="store_true",
        default=False,
        help="Print a per-job summary instead of individual entries.",
    )
    p.set_defaults(func=cmd_runlog)


def cmd_runlog(args: argparse.Namespace) -> None:  # pragma: no cover – thin I/O wrapper
    """Execute the ``runlog`` subcommand.

    Loads entries from the run-log file, applies any filters requested via
    *args*, then prints either a detailed table or a per-job summary.
    """
    log_path = Path(args.log)
    log = RunLog(log_path)
    entries = log.load()

    # --- filter by job name ---------------------------------------------------
    if args.job:
        job_lower = args.job.lower()
        entries = [e for e in entries if e.job_name.lower() == job_lower]

    # --- filter by status -----------------------------------------------------
    if args.status:
        entries = [e for e in entries if e.status == args.status]

    # --- keep only the N most recent ------------------------------------------
    if args.last is not None:
        entries = entries[-args.last :]

    if not entries:
        print("No run-log entries match the given filters.")
        return

    if args.summary:
        print(format_runlog_summary(entries))
    else:
        print(format_runlog_table(entries))
