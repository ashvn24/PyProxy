"""TLS termination and certificate management package.

Example::

    from pyproxy.ssl import TLSContextFactory

    ssl_context = TLSContextFactory.create_server_context(tls_config)
"""

from __future__ import annotations

from pyproxy.ssl.context import TLSContextFactory

__all__: list[str] = [
    "TLSContextFactory",
]
