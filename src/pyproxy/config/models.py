"""Configuration models for PyProxy.

All configuration is represented as frozen dataclasses with validation
in ``__post_init__``. Models are immutable after construction — a config
reload creates entirely new model instances.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from pyproxy.exceptions.config import ConfigValidationError


def _validate_port(field: str, value: int) -> None:
    """Validate that a port number is within the valid range.

    Args:
        field: Configuration field name for error reporting.
        value: The port number to validate.

    Raises:
        ConfigValidationError: If the port is outside 1-65535.
    """
    if not 1 <= value <= 65535:
        raise ConfigValidationError(
            field=field,
            value=value,
            reason="Port must be between 1 and 65535",
        )


def _validate_positive(field: str, value: int | float) -> None:
    """Validate that a numeric value is positive.

    Args:
        field: Configuration field name for error reporting.
        value: The numeric value to validate.

    Raises:
        ConfigValidationError: If the value is not positive.
    """
    if value <= 0:
        raise ConfigValidationError(
            field=field,
            value=value,
            reason="Value must be positive",
        )


def _validate_non_negative(field: str, value: int | float) -> None:
    """Validate that a numeric value is non-negative.

    Args:
        field: Configuration field name for error reporting.
        value: The numeric value to validate.

    Raises:
        ConfigValidationError: If the value is negative.
    """
    if value < 0:
        raise ConfigValidationError(
            field=field,
            value=value,
            reason="Value must be non-negative",
        )


_VALID_LOG_LEVELS = frozenset({"debug", "info", "warning", "error", "critical"})
_VALID_LOG_FORMATS = frozenset({"json", "text"})


@dataclasses.dataclass(frozen=True, slots=True)
class ServerConfig:
    """TCP server binding and connection configuration.

    Attributes:
        bind_host: Address to bind the server to.
        bind_port: Port number to listen on.
        backlog: Maximum number of pending connections in the listen queue.
        keepalive_timeout: Seconds to keep idle connections alive.
        read_timeout: Seconds to wait for data from the client.
        write_timeout: Seconds to wait for data to be written to the client.
        max_connections: Maximum concurrent connections (0 = unlimited).
        shutdown_timeout: Seconds to wait for graceful shutdown.
    """

    bind_host: str = "0.0.0.0"
    bind_port: int = 8080
    backlog: int = 1024
    keepalive_timeout: float = 75.0
    read_timeout: float = 30.0
    write_timeout: float = 30.0
    max_connections: int = 0
    shutdown_timeout: float = 30.0

    def __post_init__(self) -> None:
        """Validate server configuration values."""
        _validate_port("server.bind_port", self.bind_port)
        _validate_positive("server.backlog", self.backlog)
        _validate_positive("server.keepalive_timeout", self.keepalive_timeout)
        _validate_positive("server.read_timeout", self.read_timeout)
        _validate_positive("server.write_timeout", self.write_timeout)
        _validate_non_negative("server.max_connections", self.max_connections)
        _validate_positive("server.shutdown_timeout", self.shutdown_timeout)


@dataclasses.dataclass(frozen=True, slots=True)
class LoggingConfig:
    """Logging configuration.

    Attributes:
        level: Minimum log level.
        format: Output format — ``"json"`` for structured or ``"text"`` for human-readable.
        access_log: Whether to emit access logs.
        access_log_path: File path for access logs (empty string = stdout only).
        error_log_path: File path for error logs (empty string = stderr only).
        max_file_size_bytes: Maximum log file size before rotation.
        backup_count: Number of rotated log files to retain.
    """

    level: str = "info"
    format: str = "json"
    access_log: bool = True
    access_log_path: str = ""
    error_log_path: str = ""
    max_file_size_bytes: int = 10_485_760  # 10 MB
    backup_count: int = 5

    def __post_init__(self) -> None:
        """Validate logging configuration values."""
        if self.level not in _VALID_LOG_LEVELS:
            raise ConfigValidationError(
                field="logging.level",
                value=self.level,
                reason=f"Must be one of: {', '.join(sorted(_VALID_LOG_LEVELS))}",
            )
        if self.format not in _VALID_LOG_FORMATS:
            raise ConfigValidationError(
                field="logging.format",
                value=self.format,
                reason=f"Must be one of: {', '.join(sorted(_VALID_LOG_FORMATS))}",
            )
        _validate_positive("logging.max_file_size_bytes", self.max_file_size_bytes)
        _validate_non_negative("logging.backup_count", self.backup_count)


@dataclasses.dataclass(frozen=True, slots=True)
class UpstreamTargetConfig:
    """Configuration for a single upstream backend server.

    Attributes:
        host: Upstream server hostname or IP.
        port: Upstream server port.
        weight: Relative weight for weighted load balancing (higher = more traffic).
        max_connections: Maximum connections to this upstream (0 = unlimited).
    """

    host: str = "127.0.0.1"
    port: int = 8000
    weight: int = 1
    max_connections: int = 0

    def __post_init__(self) -> None:
        """Validate upstream target configuration."""
        if not self.host:
            raise ConfigValidationError(
                field="upstream.target.host",
                value=self.host,
                reason="Host must not be empty",
            )
        _validate_port("upstream.target.port", self.port)
        _validate_positive("upstream.target.weight", self.weight)
        _validate_non_negative("upstream.target.max_connections", self.max_connections)


@dataclasses.dataclass(frozen=True, slots=True)
class UpstreamConfig:
    """Upstream pool configuration.

    Attributes:
        targets: List of backend server targets.
        connect_timeout: Seconds to wait for upstream connection.
        read_timeout: Seconds to wait for upstream response.
        write_timeout: Seconds to wait for sending data to upstream.
        max_retries: Maximum retry attempts on failure.
        retry_delay: Seconds between retry attempts.
        pool_size: Maximum connections per upstream target.
    """

    targets: tuple[UpstreamTargetConfig, ...] = ()
    connect_timeout: float = 5.0
    read_timeout: float = 30.0
    write_timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 0.5
    pool_size: int = 64

    def __post_init__(self) -> None:
        """Validate upstream configuration."""
        _validate_positive("upstream.connect_timeout", self.connect_timeout)
        _validate_positive("upstream.read_timeout", self.read_timeout)
        _validate_positive("upstream.write_timeout", self.write_timeout)
        _validate_non_negative("upstream.max_retries", self.max_retries)
        _validate_non_negative("upstream.retry_delay", self.retry_delay)
        _validate_positive("upstream.pool_size", self.pool_size)


@dataclasses.dataclass(frozen=True, slots=True)
class RouteConfig:
    """Configuration for a single route entry.

    Attributes:
        path: URL path prefix or pattern to match.
        upstream: Upstream pool configuration for this route.
        methods: Allowed HTTP methods. Empty tuple means all methods are allowed.
        host: Optional host header to match (for virtual host routing).
        strip_prefix: Whether to strip the matched prefix before forwarding.
    """

    path: str = "/"
    upstream: UpstreamConfig = dataclasses.field(default_factory=UpstreamConfig)
    methods: tuple[str, ...] = ()
    host: str = ""
    strip_prefix: bool = False

    def __post_init__(self) -> None:
        """Validate route configuration."""
        if not self.path:
            raise ConfigValidationError(
                field="route.path",
                value=self.path,
                reason="Route path must not be empty",
            )
        if not self.path.startswith("/"):
            raise ConfigValidationError(
                field="route.path",
                value=self.path,
                reason="Route path must start with '/'",
            )


@dataclasses.dataclass(frozen=True, slots=True)
class TlsConfig:
    """TLS/SSL configuration.

    Attributes:
        enabled: Whether TLS is enabled.
        cert_path: Path to the TLS certificate file.
        key_path: Path to the TLS private key file.
        ca_path: Path to CA bundle for client certificate verification (mTLS).
        min_version: Minimum TLS protocol version.
    """

    enabled: bool = False
    cert_path: str = ""
    key_path: str = ""
    ca_path: str = ""
    min_version: str = "1.2"

    def __post_init__(self) -> None:
        """Validate TLS configuration."""
        if self.enabled:
            if not self.cert_path:
                raise ConfigValidationError(
                    field="tls.cert_path",
                    value=self.cert_path,
                    reason="TLS certificate path is required when TLS is enabled",
                )
            if not self.key_path:
                raise ConfigValidationError(
                    field="tls.key_path",
                    value=self.key_path,
                    reason="TLS key path is required when TLS is enabled",
                )
        valid_versions = frozenset({"1.2", "1.3"})
        if self.min_version not in valid_versions:
            raise ConfigValidationError(
                field="tls.min_version",
                value=self.min_version,
                reason=f"Must be one of: {', '.join(sorted(valid_versions))}",
            )


@dataclasses.dataclass(frozen=True, slots=True)
class RateLimiterConfig:
    """Rate Limiter configuration."""

    enabled: bool = False
    rate: float = 100.0
    burst: int = 200


@dataclasses.dataclass(frozen=True, slots=True)
class CORSConfig:
    """CORS configuration."""

    enabled: bool = False
    allow_origins: tuple[str, ...] = ("*",)
    allow_methods: tuple[str, ...] = ("GET", "POST", "PUT", "DELETE", "OPTIONS")
    allow_headers: tuple[str, ...] = ("*",)


@dataclasses.dataclass(frozen=True, slots=True)
class SecurityConfig:
    """Security configuration."""

    rate_limiter: RateLimiterConfig = dataclasses.field(default_factory=RateLimiterConfig)
    cors: CORSConfig = dataclasses.field(default_factory=CORSConfig)


@dataclasses.dataclass(frozen=True, slots=True)
class CacheConfig:
    """Cache configuration.

    Attributes:
        enabled: Whether caching is enabled.
        max_size: Maximum entries in cache.
        ttl: Time-to-live for cached responses in seconds.
    """

    enabled: bool = False
    max_size: int = 1000
    ttl: float = 60.0


@dataclasses.dataclass(frozen=True, slots=True)
class ProxyConfig:
    """Root configuration model for PyProxy.

    This is the top-level configuration dataclass that aggregates all
    subsystem configurations. Constructed by :class:`ConfigLoader` after
    parsing and validating a configuration file.

    Attributes:
        server: TCP server configuration.
        logging: Logging configuration.
        routes: Ordered list of route configurations.
        tls: TLS/SSL configuration.
        cache: Response cache configuration.
        security: Security and rate limiting configuration.
    """

    server: ServerConfig = dataclasses.field(default_factory=ServerConfig)
    logging: LoggingConfig = dataclasses.field(default_factory=LoggingConfig)
    routes: tuple[RouteConfig, ...] = ()
    tls: TlsConfig = dataclasses.field(default_factory=TlsConfig)
    cache: CacheConfig = dataclasses.field(default_factory=CacheConfig)
    security: SecurityConfig = dataclasses.field(default_factory=SecurityConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProxyConfig:
        """Create a ProxyConfig from a raw dictionary.

        Parses nested dictionaries into their corresponding dataclass models.
        Unknown top-level keys are silently ignored to support forward
        compatibility.

        Args:
            data: Raw configuration dictionary (e.g., from YAML/JSON/TOML).

        Returns:
            A fully validated ProxyConfig instance.

        Raises:
            ConfigValidationError: If any configuration value is invalid.
        """
        server_data = data.get("server", {})
        logging_data = data.get("logging", {})
        tls_data = data.get("tls", {})
        cache_data = data.get("cache", {})
        security_data = data.get("security", {})
        routes_data = data.get("routes", [])

        server = ServerConfig(**server_data) if server_data else ServerConfig()
        logging_cfg = LoggingConfig(**logging_data) if logging_data else LoggingConfig()
        tls = TlsConfig(**tls_data) if tls_data else TlsConfig()
        cache = CacheConfig(**cache_data) if cache_data else CacheConfig()

        rate_data = security_data.get("rate_limiter", {}) if isinstance(security_data, dict) else {}
        rate_cfg = RateLimiterConfig(**rate_data) if rate_data else RateLimiterConfig()
        cors_data = security_data.get("cors", {}) if isinstance(security_data, dict) else {}
        cors_cfg = CORSConfig(**cors_data) if cors_data else CORSConfig()
        security = SecurityConfig(rate_limiter=rate_cfg, cors=cors_cfg)

        routes: list[RouteConfig] = []
        for route_data in routes_data:
            upstream_data = route_data.pop("upstream", {})
            targets_data = upstream_data.pop("targets", []) if upstream_data else []

            targets = tuple(
                UpstreamTargetConfig(**target) for target in targets_data
            )
            upstream = UpstreamConfig(
                targets=targets,
                **upstream_data,
            ) if upstream_data else UpstreamConfig(targets=targets)

            methods_raw = route_data.pop("methods", [])
            methods = tuple(method.upper() for method in methods_raw)

            routes.append(RouteConfig(
                upstream=upstream,
                methods=methods,
                **route_data,
            ))

        return cls(
            server=server,
            logging=logging_cfg,
            routes=tuple(routes),
            tls=tls,
            cache=cache,
            security=security,
        )
