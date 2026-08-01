"""CLI command handlers for PyProxy.

Each subcommand is implemented as a standalone function that receives
the parsed arguments namespace. This keeps command logic testable
without invoking the full argument parser.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse


def cmd_version(args: argparse.Namespace) -> int:
    """Print the PyProxy version and exit.

    Args:
        args: Parsed CLI arguments (unused for this command).

    Returns:
        Exit code (always 0).
    """
    from pyproxy import __version__

    sys.stdout.write(f"pyproxy {__version__}\n")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate a configuration file and report any errors.

    Loads and validates the specified configuration file, printing
    either a success message or detailed validation errors.

    Args:
        args: Parsed CLI arguments. Must include ``config`` (file path).

    Returns:
        Exit code: 0 on success, 1 on validation failure.
    """
    from pyproxy.config.loader import ConfigLoader
    from pyproxy.exceptions import PyProxyError

    config_path = Path(args.config)
    sys.stdout.write(f"Validating configuration: {config_path}\n")

    try:
        loader = ConfigLoader(config_path)
        config = loader.load()
    except PyProxyError as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        if exc.context:
            for key, value in exc.context.items():
                sys.stderr.write(f"  {key}: {value}\n")
        return 1
    except Exception as exc:
        sys.stderr.write(f"ERROR: Unexpected error: {exc}\n")
        return 1

    sys.stdout.write("Configuration is valid.\n")
    sys.stdout.write(f"  Server: {config.server.bind_host}:{config.server.bind_port}\n")
    sys.stdout.write(f"  Routes: {len(config.routes)}\n")
    sys.stdout.write(f"  TLS:    {'enabled' if config.tls.enabled else 'disabled'}\n")
    sys.stdout.write(f"  Log:    {config.logging.level} ({config.logging.format})\n")
    return 0


def cmd_start(args: argparse.Namespace) -> int:
    """Start the PyProxy reverse proxy server.

    Args:
        args: Parsed CLI arguments. Must include ``config`` (file path).

    Returns:
        Exit code.
    """
    from pyproxy.proxy_app import Proxy

    try:
        proxy = Proxy(config_path=args.config)
        proxy.run()
        return 0
    except Exception as exc:
        sys.stderr.write(f"ERROR: Failed to start PyProxy: {exc}\n")
        return 1


def cmd_stop(args: argparse.Namespace) -> int:
    """Stop a running PyProxy server.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Exit code.
    """
    sys.stdout.write("pyproxy stop: Not yet implemented (Phase 2+)\n")
    return 0


def cmd_reload(args: argparse.Namespace) -> int:
    """Reload the configuration of a running PyProxy server.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Exit code.
    """
    sys.stdout.write("pyproxy reload: Not yet implemented (Phase 2+)\n")
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    """Display the current effective configuration.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Exit code.
    """
    sys.stdout.write("pyproxy config: Not yet implemented (Phase 2+)\n")
    return 0


def cmd_benchmark(args: argparse.Namespace) -> int:
    """Run benchmarks against the proxy.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Exit code.
    """
    sys.stdout.write("pyproxy benchmark: Not yet implemented\n")
    return 0
