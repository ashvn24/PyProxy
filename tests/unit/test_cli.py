"""Tests for the CLI argument parser and command dispatch."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyproxy.cli.main import create_parser, main


class TestParser:
    """Tests for the CLI argument parser structure."""

    def test_version_subcommand(self):
        parser = create_parser()
        args = parser.parse_args(["version"])
        assert args.command == "version"

    def test_validate_subcommand(self):
        parser = create_parser()
        args = parser.parse_args(["validate", "config.yaml"])
        assert args.command == "validate"
        assert args.config == "config.yaml"

    def test_start_subcommand(self):
        parser = create_parser()
        args = parser.parse_args(["start", "config.yaml"])
        assert args.command == "start"
        assert args.config == "config.yaml"

    def test_start_with_host_port(self):
        parser = create_parser()
        args = parser.parse_args(["start", "config.yaml", "--host", "127.0.0.1", "--port", "9090"])
        assert args.host == "127.0.0.1"
        assert args.port == 9090

    def test_no_subcommand(self):
        parser = create_parser()
        args = parser.parse_args([])
        assert args.command is None


class TestMainDispatch:
    """Tests for the main CLI dispatch function."""

    def test_version_returns_zero(self, capsys):
        exit_code = main(["version"])
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "pyproxy" in captured.out

    def test_no_command_returns_zero(self, capsys):
        exit_code = main([])
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "pyproxy" in captured.out.lower() or "usage" in captured.out.lower()

    def test_validate_valid_config(self, capsys, sample_yaml_file):
        exit_code = main(["validate", str(sample_yaml_file)])
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "valid" in captured.out.lower()

    def test_validate_missing_config(self, capsys, tmp_dir):
        missing = tmp_dir / "nonexistent.yaml"
        exit_code = main(["validate", str(missing)])
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "error" in captured.err.lower()

    def test_validate_invalid_config(self, capsys, tmp_dir):
        bad_config = tmp_dir / "bad.yaml"
        bad_config.write_text(
            "server:\n  bind_port: 99999\n",
            encoding="utf-8",
        )
        exit_code = main(["validate", str(bad_config)])
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "error" in captured.err.lower()

    def test_start_stub(self, capsys):
        exit_code = main(["start", "config.yaml"])
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "not yet implemented" in captured.out.lower()

    def test_stop_stub(self, capsys):
        exit_code = main(["stop"])
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "not yet implemented" in captured.out.lower()

    def test_reload_stub(self, capsys):
        exit_code = main(["reload"])
        assert exit_code == 0

    def test_benchmark_stub(self, capsys):
        exit_code = main(["benchmark"])
        assert exit_code == 0

    def test_config_stub(self, capsys):
        exit_code = main(["config"])
        assert exit_code == 0
