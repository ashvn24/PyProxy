"""IP Address Allowlist and Denylist Filtering.

Supports individual IP address and CIDR block checking using stdlib ipaddress.
"""

from __future__ import annotations

import ipaddress
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

logger = logging.getLogger("pyproxy.security.ip_filter")


class IPFilter:
    """Evaluates client IP against configured allowlists and denylists."""

    def __init__(
        self,
        allowlist: Iterable[str] | None = None,
        denylist: Iterable[str] | None = None,
    ) -> None:
        """Initialize IPFilter.

        Args:
            allowlist: Iterable of IP strings or CIDR subnets allowed.
            denylist: Iterable of IP strings or CIDR subnets blocked.
        """
        self.allow_networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = [
            ipaddress.ip_network(item, strict=False) for item in (allowlist or [])
        ]
        self.deny_networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = [
            ipaddress.ip_network(item, strict=False) for item in (denylist or [])
        ]

    def is_allowed(self, ip_str: str) -> bool:
        """Check if client IP address is allowed.

        Args:
            ip_str: Client IP address string.

        Returns:
            True if permitted; False if blocked.
        """
        if not ip_str:
            return True

        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            logger.warning("Invalid IP address string received: '%s'", ip_str)
            return False

        # 1. Denylist check
        for net in self.deny_networks:
            if ip_obj in net:
                logger.warning("IP %s blocked by denylist subnet %s", ip_str, net)
                return False

        # 2. Allowlist check (if non-empty)
        if self.allow_networks:
            for net in self.allow_networks:
                if ip_obj in net:
                    return True
            logger.warning("IP %s blocked: not in allowlist", ip_str)
            return False

        return True
