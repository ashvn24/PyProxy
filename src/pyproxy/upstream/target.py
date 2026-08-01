"""Upstream backend target representation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pyproxy.config.models import UpstreamTargetConfig


@dataclass(slots=True)
class UpstreamTarget:
    """Represents a single backend server endpoint.

    Attributes:
        host: Hostname or IP address of upstream server.
        port: Port number of upstream server.
        weight: Traffic weight integer.
        max_connections: Maximum concurrent connection limit (0 = unlimited).
        is_healthy: Operational health flag (managed by HealthChecker).
        active_connections: Counter of active connections to this target.
    """

    host: str = "127.0.0.1"
    port: int = 8000
    weight: int = 1
    max_connections: int = 0
    is_healthy: bool = True
    active_connections: int = 0

    @classmethod
    def from_config(cls, config: UpstreamTargetConfig) -> UpstreamTarget:
        """Construct UpstreamTarget from UpstreamTargetConfig.

        Args:
            config: UpstreamTargetConfig dataclass.

        Returns:
            Constructed UpstreamTarget instance.
        """
        return cls(
            host=config.host,
            port=config.port,
            weight=config.weight,
            max_connections=config.max_connections,
        )

    @property
    def endpoint(self) -> str:
        """Get host:port endpoint string.

        Returns:
            Formatted "host:port" string.
        """
        return f"{self.host}:{self.port}"
