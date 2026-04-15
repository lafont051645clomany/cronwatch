"""Tests for the cronwatch CLI layer."""

from unittest.mock import MagicMock, patch

import pytest

from cronwatch.cli import build_parser, main


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------

def test_parser_check_command():
    parser = build_parser()
    args = parser.parse_args(["check"])
    assert args.command == "check"
    assert args.config is None


def test_parser_check_with_config():
    parser = build_parser()
    args = parser.parse_args(["--config", "my.toml", "check"])
    assert args.config == "my.toml"


def test_parser_report_command():
    parser = build_parser()
    args = parser.parse_args(["report"])
    assert args.command == "report"
    assert args.job is None


def test_parser_report_with_job():
    parser = build_parser()
    args = parser.parse_args(["report", "--job", "backup"])
    assert args.job == "backup"


def test_parser_ping_start():
    parser = build_parser()
    args = parser.parse_args(["ping", "backup", "start"])
    assert args.command == "ping"
    assert args.job == "backup"
    assert args.event == "start"


def test_parser_ping_invalid_event():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["ping", "backup", "unknown"])


# ---------------------------------------------------------------------------
# Integration-style tests using mocks
# ---------------------------------------------------------------------------

@patch("cronwatch.cli.Watcher")
@patch("cronwatch.cli.JobTracker")
@patch("cronwatch.cli.load_config")
def test_cmd_check_no_alerts(mock_load, mock_tracker_cls, mock_watcher_cls, capsys):
    mock_watcher = MagicMock()
    mock_watcher.check_all.return_value = []
    mock_watcher_cls.return_value = mock_watcher
    rc = main(["check"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "nominal" in captured.out


@patch("cronwatch.cli.Watcher")
@patch("cronwatch.cli.JobTracker")
@patch("cronwatch.cli.load_config")
def test_cmd_check_with_alerts(mock_load, mock_tracker_cls, mock_watcher_cls, capsys):
    mock_watcher = MagicMock()
    mock_watcher.check_all.return_value = ["alert1"]
    mock_watcher_cls.return_value = mock_watcher
    rc = main(["check"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "1 alert" in captured.out


@patch("cronwatch.cli.JobTracker")
def test_cmd_ping_start(mock_tracker_cls, capsys):
    mock_tracker = MagicMock()
    mock_tracker_cls.return_value = mock_tracker
    rc = main(["ping", "backup", "start"])
    assert rc == 0
    mock_tracker.start.assert_called_once_with("backup")


@patch("cronwatch.cli.JobTracker")
def test_cmd_ping_success(mock_tracker_cls, capsys):
    mock_tracker = MagicMock()
    mock_tracker.finish.return_value = MagicMock()
    mock_tracker_cls.return_value = mock_tracker
    rc = main(["ping", "backup", "success"])
    assert rc == 0
    mock_tracker.finish.assert_called_once_with("backup", success=True)


@patch("cronwatch.cli.JobTracker")
def test_cmd_ping_failure_no_active_run(mock_tracker_cls, capsys):
    mock_tracker = MagicMock()
    mock_tracker.finish.return_value = None
    mock_tracker_cls.return_value = mock_tracker
    rc = main(["ping", "backup", "failure"])
    assert rc == 1
