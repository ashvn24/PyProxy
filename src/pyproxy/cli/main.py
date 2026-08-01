"""CLI entry point for PyProxy.

Provides the ``pyproxy`` command-line interface with subcommands for
starting, stopping, and managing the reverse proxy.

Usage::

    pyproxy version
    pyproxy validate config.yaml
    pyproxy start config.yaml
"""

from __future__ import annotations

import argparse
import sys


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser.

    Returns:
        The configured ArgumentParser with all subcommands.
    """
    parser = argparse.ArgumentParser(
        prog="pyproxy",
        description="PyProxy — A modern, production-grade reverse proxy built on Python asyncio.",
        epilog="See https://github.com/pyproxy/pyproxy for documentation.",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        title="commands",
        description="Available commands",
        help="Run 'pyproxy <command> --help' for more information.",
    )

    # --- version ---
    subparsers.add_parser(
        "version",
        help="Print the PyProxy version.",
    )

    # --- validate ---
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate a configuration file.",
    )
    validate_parser.add_argument(
        "config",
        type=str,
        help="Path to the configuration file to validate.",
    )

    # --- start ---
    start_parser = subparsers.add_parser(
        "start",
        help="Start the reverse proxy server.",
    )
    start_parser.add_argument(
        "config",
        type=str,
        help="Path to the configuration file.",
    )
    start_parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Override the bind host (default: from config).",
    )
    start_parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Override the bind port (default: from config).",
    )

    # --- stop ---
    subparsers.add_parser(
        "stop",
        help="Stop the running proxy server.",
    )

    # --- reload ---
    subparsers.add_parser(
        "reload",
        help="Reload the proxy configuration without downtime.",
    )

    # --- config ---
    subparsers.add_parser(
        "config",
        help="Display the effective configuration.",
    )

    # --- benchmark ---
    subparsers.add_parser(
        "benchmark",
        help="Run performance benchmarks.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point.

    Parses command-line arguments and dispatches to the appropriate
    command handler.

    Args:
        argv: Command-line arguments. Defaults to ``sys.argv[1:]``.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    from pyproxy.cli.commands import (
        cmd_benchmark,
        cmd_config,
        cmd_reload,
        cmd_start,
        cmd_stop,
        cmd_validate,
        cmd_version,
    )

    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    command_handlers: dict[str, object] = {
        "version": cmd_version,
        "validate": cmd_validate,
        "start": cmd_start,
        "stop": cmd_stop,
        "reload": cmd_reload,
        "config": cmd_config,
        "benchmark": cmd_benchmark,
    }

    handler = command_handlers.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    return handler(args)  # type: ignore[operator]


def cli_entry_point() -> None:
    """Entry point for the ``pyproxy`` console script.

    This function is registered in ``pyproject.toml`` under
    ``[project.scripts]`` and is called when the user runs ``pyproxy``
    from the command line.
    """
    sys.exit(main())
