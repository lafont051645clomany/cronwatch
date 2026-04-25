"""Tests for cronwatch.suppression_reporter."""
from __future__ import annotations

from cronwatch.suppression import SuppressionRule, Suppressor
from cronwatch.suppression_reporter import format_suppression_table
from cronwatch.tracker import JobStatus


def test_empty_rules_returns_message():
    result = format_suppression_table([])
    assert "No suppression rules" in result


def test_table_contains_rule_name():
    rule = SuppressionRule(name="skip-nightly")
    result = format_suppression_table([rule])
    assert "skip-nightly" in result


def test_table_shows_wildcard_for_any_job():
    rule = SuppressionRule(name="r", job_names=[])
    result = format_suppression_table([rule])
    assert "*" in result


def test_table_shows_job_names():
    rule = SuppressionRule(name="r", job_names=["backup", "cleanup"])
    result = format_suppression_table([rule])
    assert "backup,cleanup" in result


def test_table_shows_statuses():
    rule = SuppressionRule(name="r", statuses=[JobStatus.FAILURE])
    result = format_suppression_table([rule])
    assert "failure" in result.lower()


def test_table_shows_max_duration():
    rule = SuppressionRule(name="r", max_duration=120.0)
    result = format_suppression_table([rule])
    assert "120.0" in result


def test_table_shows_reason():
    rule = SuppressionRule(name="r", reason="planned maintenance")
    result = format_suppression_table([rule])
    assert "planned maintenance" in result


def test_table_has_header_separator():
    rule = SuppressionRule(name="r")
    result = format_suppression_table([rule])
    lines = result.splitlines()
    # second line should be all dashes
    assert set(lines[1].strip()) == {"-"}


def test_multiple_rules_all_present():
    rules = [
        SuppressionRule(name="r1", job_names=["alpha"]),
        SuppressionRule(name="r2", job_names=["beta"]),
    ]
    result = format_suppression_table(rules)
    assert "r1" in result
    assert "r2" in result
    assert "alpha" in result
    assert "beta" in result
