"""Route matching rule and path pattern definitions.

Supports longest-prefix, exact, regex, host, wildcard, and method matching.
"""

from __future__ import annotations

import enum
import fnmatch
import re
from typing import TYPE_CHECKING, Any

from pyproxy.config.models import RouteConfig, UpstreamConfig
from pyproxy.exceptions.config import ConfigValidationError
from pyproxy.exceptions.routing import RoutingError

if TYPE_CHECKING:
    from pyproxy.protocol.request import HTTPRequest


class RouteMatchType(enum.Enum):
    """Supported route path matching strategies."""

    PREFIX = "prefix"
    EXACT = "exact"
    REGEX = "regex"
    WILDCARD = "wildcard"


class RouteRule:
    """Encapsulates routing conditions and upstream target mapping.

    Attributes:
        path_pattern: Target path string or pattern.
        match_type: Matching algorithm to apply (PREFIX, EXACT, REGEX, WILDCARD).
        methods: Set of allowed HTTP methods (uppercase). Empty = allow all.
        host_pattern: Optional Host header pattern (supports wildcards e.g. '*.example.com').
        priority: Numeric evaluation priority (higher numbers evaluated first).
        strip_prefix: Whether to strip matched path prefix when forwarding upstream.
        upstream_config: Configured upstream pool for this route.
    """

    __slots__ = (
        "path_pattern",
        "match_type",
        "methods",
        "host_pattern",
        "priority",
        "strip_prefix",
        "upstream_config",
        "_compiled_regex",
        "_target_url",
        "_target_host",
        "_target_port",
        "_target_ssl",
        "_target_path_prefix",
    )

    def __init__(
        self,
        path_pattern: str,
        match_type: RouteMatchType = RouteMatchType.PREFIX,
        methods: set[str] | None = None,
        host_pattern: str = "",
        priority: int = 0,
        strip_prefix: bool = False,
        upstream_config: UpstreamConfig | None = None,
    ) -> None:
        """Initialize RouteRule.

        Args:
            path_pattern: Path string, regex, or wildcard pattern.
            match_type: Matching type enum value.
            methods: Set of HTTP methods to match.
            host_pattern: Host header matching string.
            priority: Priority weighting integer.
            strip_prefix: Flag indicating whether prefix should be stripped.
            upstream_config: UpstreamConfig for target servers.
        """
        self.path_pattern: str = path_pattern
        self.match_type: RouteMatchType = match_type
        self.methods: set[str] = {m.upper() for m in methods} if methods else set()
        self.host_pattern: str = host_pattern
        self.priority: int = priority
        self.strip_prefix: bool = strip_prefix
        self.upstream_config: UpstreamConfig = upstream_config or UpstreamConfig()

        self._compiled_regex: re.Pattern[str] | None = None
        if match_type == RouteMatchType.REGEX:
            try:
                self._compiled_regex = re.compile(path_pattern)
            except re.error as exception:
                raise ConfigValidationError(
                    field="route.path",
                    value=path_pattern,
                    reason=f"Invalid regular expression: {exception}",
                ) from exception

    @classmethod
    def from_config(cls, config: RouteConfig) -> RouteRule:
        """Factory method to construct RouteRule from RouteConfig model.

        Args:
            config: RouteConfig dataclass from PyProxy configuration.

        Returns:
            Constructed RouteRule instance.
        """
        # Determine match type automatically
        path = config.path
        if path.startswith("^") or ".*" in path or "(?" in path:
            match_type = RouteMatchType.REGEX
        elif "*" in path:
            match_type = RouteMatchType.WILDCARD
        else:
            match_type = RouteMatchType.PREFIX

        return cls(
            path_pattern=config.path,
            match_type=match_type,
            methods=set(config.methods),
            host_pattern=config.host,
            priority=len(config.path) if match_type == RouteMatchType.PREFIX else 100,
            strip_prefix=config.strip_prefix,
            upstream_config=config.upstream,
        )

    def matches(self, request: HTTPRequest) -> bool:
        """Evaluate if an incoming HTTPRequest satisfies all route criteria.

        Args:
            request: Incoming HTTPRequest model.

        Returns:
            True if all method, host, and path criteria match.
        """
        # 1. Method check
        if self.methods and request.method.upper() not in self.methods:
            return False

        # 2. Host check
        if self.host_pattern:
            req_host = request.host.split(":")[0].lower()  # Strip port if present
            host_pat = self.host_pattern.lower()
            if "*" in host_pat:
                if not fnmatch.fnmatch(req_host, host_pat):
                    return False
            elif req_host != host_pat:
                return False

        # 3. Path check
        return self.matches_path(request.path)

    def matches_path(self, request_path: str) -> bool:
        """Evaluate if path string matches the rule's path pattern.

        Args:
            request_path: URL path to test.

        Returns:
            True if path matches.
        """
        if self.match_type == RouteMatchType.EXACT:
            return request_path == self.path_pattern

        if self.match_type == RouteMatchType.PREFIX:
            if self.path_pattern == "/":
                return True
            return request_path == self.path_pattern or request_path.startswith(self.path_pattern + "/") or request_path.startswith(self.path_pattern)

        if self.match_type == RouteMatchType.REGEX:
            if self._compiled_regex:
                return self._compiled_regex.search(request_path) is not None
            return False

        if self.match_type == RouteMatchType.WILDCARD:
            return fnmatch.fnmatch(request_path, self.path_pattern)

        return False

    def rewrite_path(self, original_path: str) -> str:
        """Rewrite request path if strip_prefix is enabled.

        Args:
            original_path: Input URL path.

        Returns:
            Rewritten target URL path for upstream forwarding.
        """
        if not self.strip_prefix or self.match_type != RouteMatchType.PREFIX:
            return original_path

        if self.path_pattern == "/":
            return original_path

        if original_path.startswith(self.path_pattern):
            rewritten = original_path[len(self.path_pattern):]
            if not rewritten.startswith("/"):
                rewritten = "/" + rewritten
            return rewritten

        return original_path
