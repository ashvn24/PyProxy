"""Unit tests for TLSContextFactory."""

from __future__ import annotations

import pytest

from pyproxy.config.models import TlsConfig
from pyproxy.exceptions import TlsError
from pyproxy.ssl import TLSContextFactory


class TestTLSContextFactory:
    """Tests for TLSContextFactory."""

    def test_disabled_tls_raises(self):
        config = TlsConfig(enabled=False)
        with pytest.raises(TlsError, match="disabled"):
            TLSContextFactory.create_server_context(config)

    def test_missing_cert_file_raises(self, tmp_dir):
        config = TlsConfig(
            enabled=True,
            cert_path=str(tmp_dir / "nonexistent.crt"),
            key_path=str(tmp_dir / "nonexistent.key"),
        )
        with pytest.raises(TlsError, match="not found"):
            TLSContextFactory.create_server_context(config)
