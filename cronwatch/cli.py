"""CLI entry point for cronwatch."""

import argparse
import sys
from pathlib import Path

from cronwatch.config import load_config
from cronwatch.tracker import JobTracker
from cronwatch.watcher import Watcher
from cronwatch.reporter import summarise_runs, format_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronwatch",
        description="Monitor cron job execution times and alert on delays or failures.",
    )
    parser.add_argument(
        "--config",
        metavar="PATH",
        help="Path to cronwatch.toml config file.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # check sub-command
    subparsers.add_parser("check", help="Check all jobs for overdue or failed runs.")

    # report sub-command
    report_parser = subparsers.add_parser("report", help="Print a summary report.")
    report_parser.add_argument(
        "--job",
        metavar="NAME",
        help="Limit report to a specific job name.",
    )

    # ping sub-command
    ping_parser = subparsers.add_parser(
        "ping", help="Record a job start or finish event."
    )
    ping_parser.add_argument("job", help="Job name to ping.")
    ping_parser.add_argument(
        "event",
        choices=["start", "success", "failure"],
        help="Event type to record.",
    )

    return parser


def cmd_check(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    tracker = JobTracker()
    watcher = Watcher(cfg, tracker)
    alerts_sent = watcher.check_all()
    if alerts_sent:
        print(f"cronwatch: {len(alerts_sent)} alert(s) dispatched.")
    else:
        print("cronwatch: all jobs nominal.")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    tracker = JobTracker()
    job_names = [args.job] if args.job else [j.name for j in cfg.jobs]
    for name in job_names:
        runs = tracker.history(name)
        if not runs:
            print(f"[{name}] no runs recorded.")
            continue
        summary = summarise_runs(name, runs)
        print(format_report(summary))
    return 0


def cmd_ping(args: argparse.Namespace) -> int:
    tracker = JobTracker()
    if args.event == "start":
        tracker.start(args.job)
        print(f"cronwatch: recorded start for '{args.job}'.")
    elif args.event == "success":
        run = tracker.finish(args.job, success=True)
        if run is None:
            print(f"cronwatch: no active run found for '{args.job}'.", file=sys.stderr)
            return 1
        print(f"cronwatch: recorded success for '{args.job}'.")
    elif args.event == "failure":
        run = tracker.finish(args.job, success=False)
        if run is None:
            print(f"cronwatch: no active run found for '{args.job}'.", file=sys.stderr)
            return 1
        print(f"cronwatch: recorded failure for '{args.job}'.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    dispatch = {"check": cmd_check, "report": cmd_report, "ping": cmd_ping}
    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
