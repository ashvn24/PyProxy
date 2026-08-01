"""Environment variable override processing for configuration.

Environment variables with the ``PYPROXY_`` prefix override values loaded
from configuration files. Nesting is expressed with double underscores::

    PYPROXY_SERVER__BIND_PORT=9090   →  config["server"]["bind_port"] = 9090
    PYPROXY_LOGGING__LEVEL=debug     →  config["logging"]["level"] = "debug"
"""

from __future__ import annotations

import os
from typing import Any

_ENV_PREFIX = "PYPROXY_"
_NESTING_SEPARATOR = "__"


def _coerce_value(value: str) -> str | int | float | bool:
    """Attempt to coerce a string environment variable to a typed value.

    Tries, in order: bool, int, float. Falls back to string.

    Args:
        value: The raw string value from the environment.

    Returns:
        The coerced value as the most specific type possible.
    """
    # Boolean detection (case-insensitive)
    lower_value = value.lower()
    if lower_value in ("true", "yes", "1", "on"):
        return True
    if lower_value in ("false", "no", "0", "off"):
        return False

    # Integer detection
    try:
        return int(value)
    except ValueError:
        pass

    # Float detection
    try:
        return float(value)
    except ValueError:
        pass

    return value


def apply_environment_overrides(config_data: dict[str, Any]) -> dict[str, Any]:
    """Apply environment variable overrides to a configuration dictionary.

    Scans all environment variables for those starting with ``PYPROXY_``,
    strips the prefix, splits on ``__`` to determine the nesting path,
    and sets the value in the configuration dictionary. Values are
    automatically coerced from strings to their most appropriate type.

    Args:
        config_data: The base configuration dictionary to override. This
            dictionary is mutated in place and also returned.

    Returns:
        The mutated configuration dictionary with environment overrides applied.

    Examples:
        >>> import os
        >>> os.environ["PYPROXY_SERVER__BIND_PORT"] = "9090"
        >>> data = {"server": {"bind_port": 8080}}
        >>> apply_environment_overrides(data)
        {'server': {'bind_port': 9090}}
    """
    for env_key, env_value in os.environ.items():
        if not env_key.startswith(_ENV_PREFIX):
            continue

        # Strip the prefix and split into nesting path segments
        config_path = env_key[len(_ENV_PREFIX) :]
        path_segments = [segment.lower() for segment in config_path.split(_NESTING_SEPARATOR)]

        if not path_segments or not all(path_segments):
            continue

        # Walk the dict tree, creating intermediate dicts as needed
        current_level = config_data
        for segment in path_segments[:-1]:
            if segment not in current_level:
                current_level[segment] = {}
            next_level = current_level[segment]
            if not isinstance(next_level, dict):
                # If the intermediate path is not a dict, we can't nest further.
                # Skip this override to avoid corrupting existing scalar values.
                break
            current_level = next_level
        else:
            # Set the final value with type coercion
            final_key = path_segments[-1]
            current_level[final_key] = _coerce_value(env_value)

    return config_data
