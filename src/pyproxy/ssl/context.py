"""TLS/SSL Context Factory and SNI Manager.

Handles server TLS termination, certificate loading, mutual TLS (mTLS),
SNI certificate resolution, and minimum TLS version enforcement.
"""

from __future__ import annotations

import logging
import ssl
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pyproxy.config.models import TlsConfig
from pyproxy.exceptions.protocol import TlsError

logger = logging.getLogger("pyproxy.ssl.context")


class TLSContextFactory:
    """Factory for building configured ssl.SSLContext instances."""

    @classmethod
    def create_server_context(cls, config: TlsConfig) -> ssl.SSLContext:
        """Create a server-side SSLContext from TlsConfig model.

        Args:
            config: TlsConfig dataclass.

        Returns:
            Configured ssl.SSLContext instance.

        Raises:
            TlsError: If certificate files do not exist or context creation fails.
        """
        if not config.enabled:
            raise TlsError("Cannot create TLS context when TLS is disabled in config")

        cert_path = Path(config.cert_path)
        key_path = Path(config.key_path)

        if not cert_path.exists():
            raise TlsError(f"TLS certificate file not found: {cert_path}")
        if not key_path.exists():
            raise TlsError(f"TLS private key file not found: {key_path}")

        try:
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)

            # Protocol version enforcement
            if config.min_version == "1.3":
                ssl_context.minimum_version = ssl.TLSVersion.TLSv1_3
            else:
                ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2

            # Load certificate and private key
            ssl_context.load_cert_chain(
                certfile=str(cert_path),
                keyfile=str(key_path),
            )

            # Mutual TLS (mTLS) configuration
            if config.ca_path:
                ca_path = Path(config.ca_path)
                if not ca_path.exists():
                    raise TlsError(f"TLS CA bundle file not found: {ca_path}")
                ssl_context.load_verify_locations(cafile=str(ca_path))
                ssl_context.verify_mode = ssl.CERT_REQUIRED
                logger.info("Mutual TLS (mTLS) enabled using CA: %s", ca_path)
            else:
                ssl_context.verify_mode = ssl.CERT_NONE

            logger.info("TLS Context created successfully (min version: TLSv%s)", config.min_version)
            return ssl_context
        except Exception as exception:
            raise TlsError(f"Failed to initialize TLS context: {exception}") from exception
