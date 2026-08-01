"""Response compression package.

Example::

    from pyproxy.compression import Compressor

    response = Compressor.process_response(request, response)
"""

from __future__ import annotations

from pyproxy.compression.compressor import Compressor

__all__: list[str] = [
    "Compressor",
]
