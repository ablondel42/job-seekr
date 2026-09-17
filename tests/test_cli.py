"""Tests for Job Seekr CLI commands."""

import sys
from unittest.mock import patch
from main import build_parser, main


def test_cli_parser_commands():
    """Verify all subcommands and flags are recognized."""
    parser = build_parser()

    # run
    args_run = parser.parse_args(["run", "--dry-run", "--config", "custom.yaml"])
    assert args_run.command == "run"
    assert args_run.dry_run is True
    assert args_run.config == "custom.yaml"

    # daemon
    args_daemon = parser.parse_args(["daemon", "--interval", "12"])
    assert args_daemon.command == "daemon"
    assert args_daemon.interval == 12.0

    # list
    args_list = parser.parse_args(["list", "--status", "drafted", "--limit", "10"])
    assert args_list.command == "list"
    assert args_list.status == "drafted"
    assert args_list.limit == 10

    # apply
    args_apply = parser.parse_args(["apply", "42"])
    assert args_apply.command == "apply"
    assert args_apply.job_id == 42

    # test-pdf
    args_pdf = parser.parse_args(["test-pdf"])
    assert args_pdf.command == "test-pdf"


def test_cli_dry_run_execution():
    """Verify main() runs dry-run without crashing."""
    test_args = ["main.py", "run", "--dry-run"]
    with patch.object(sys, "argv", test_args):
        ret_code = main()
        assert ret_code == 0
