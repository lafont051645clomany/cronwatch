"""Tests for the metrics CLI sub-command."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest

from cronwatch.cli_metrics import add_metrics_subparser, cmd_metrics
from cronwatch.tracker import JobRun, JobStatus


def _make_run(job_name: str, status: JobStatus, duration: float = 5.0) -> JobRun:
    now = datetime.now(timezone.utc)
    run = JobRun(job_name=job_name, started_at=now)
    run.status = status
    run.finished_at = now + timedelta(seconds=duration)
    return run


@pytest.fixture()
 def parser():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers()
    add_metrics_subparser(sub)
    return p


def test_metrics_subparser_registered(parser):
    args = parser.parse_args(["metrics"])
    assert hasattr(args, "func")
    assert args.func is cmd_metrics


def test_metrics_subparser_job_flag(parser):
    args = parser.parse_args(["metrics", "--job", "backup"])
    assert args.job == "backup"


def test_metrics_subparser_top_failing_flag(parser):
    args = parser.parse_args(["metrics", "--top-failing", "3"])
    assert args.top_failing == 3


def _run_cmd(runs, extra_args=None):
    """Helper: run cmd_metrics with mocked dependencies."""
    args = argparse.Namespace(
        config=None,
        job=None,
        top_failing=0,
        **(extra_args or {}),
    )
    mock_cfg = MagicMock()
    mock_cfg.history_path = None
    mock_store = MagicMock()
    mock_store.load.return_value = runs

    with patch("cronwatch.cli_metrics.CronwatchConfig.load", return_value=mock_cfg), \
         patch("cronwatch.cli_metrics.HistoryStore", return_value=mock_store):
        return cmd_metrics(args)


def test_cmd_metrics_returns_zero_on_success():
    runs = [_make_run("backup", JobStatus.SUCCESS)]
    assert _run_cmd(runs) == 0


def test_cmd_metrics_empty_runs():
    assert _run_cmd([]) == 0


def test_cmd_metrics_filters_by_job(capsys):
    runs = [
        _make_run("backup", JobStatus.SUCCESS),
        _make_run("sync", JobStatus.FAILURE),
    ]
    args = argparse.Namespace(config=None, job="sync", top_failing=0)
    mock_cfg = MagicMock()
    mock_cfg.history_path = None
    mock_store = MagicMock()
    mock_store.load.return_value = runs

    with patch("cronwatch.cli_metrics.CronwatchConfig.load", return_value=mock_cfg), \
         patch("cronwatch.cli_metrics.HistoryStore", return_value=mock_store):
        cmd_metrics(args)

    out = capsys.readouterr().out
    assert "sync" in out
    assert "backup" not in out


def test_cmd_metrics_top_failing_mode(capsys):
    runs = [_make_run("backup", JobStatus.FAILURE) for _ in range(3)]
    args = argparse.Namespace(config=None, job=None, top_failing=1)
    mock_cfg = MagicMock()
    mock_cfg.history_path = None
    mock_store = MagicMock()
    mock_store.load.return_value = runs

    with patch("cronwatch.cli_metrics.CronwatchConfig.load", return_value=mock_cfg), \
         patch("cronwatch.cli_metrics.HistoryStore", return_value=mock_store):
        cmd_metrics(args)

    out = capsys.readouterr().out
    assert "backup" in out
    assert "failure" in out.lower()
