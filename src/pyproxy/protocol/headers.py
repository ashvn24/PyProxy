"""Case-insensitive HTTP Headers data structure.

Preserves case for display while providing case-insensitive lookup
and support for multi-valued headers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Mapping


class Headers:
    """Case-insensitive HTTP Header container.

    Maintains original header casing while allowing case-insensitive lookups,
    and supports multi-value headers (e.g., multiple ``Set-Cookie`` or ``Via`` headers).
    """

    __slots__ = ("_store",)

    def __init__(
        self,
        headers: Mapping[str, str] | Iterable[tuple[str, str]] | None = None,
    ) -> None:
        """Initialize Headers container.

        Args:
            headers: Initial headers mapping or iterable of key-value tuples.
        """
        # Store layout: lower_key -> (original_key, list[value])
        self._store: dict[str, tuple[str, list[str]]] = {}

        if headers is not None:
            if isinstance(headers, dict):
                for key, value in headers.items():
                    self.add(key, value)
            else:
                for key, value in headers:
                    self.add(key, value)

    def add(self, name: str, value: str) -> None:
        """Add a header name and value pair.

        Args:
            name: Header field name.
            value: Header field value.
        """
        lower_name: str = name.lower()
        if lower_name in self._store:
            orig_name, values = self._store[lower_name]
            values.append(value)
        else:
            self._store[lower_name] = (name, [value])

    def set(self, name: str, value: str) -> None:
        """Set a header, replacing any existing values for that header name.

        Args:
            name: Header field name.
            value: Header field value.
        """
        lower_name: str = name.lower()
        self._store[lower_name] = (name, [value])

    def get(self, name: str, default: str | None = None) -> str | None:
        """Get the first value for a header name (case-insensitive).

        Args:
            name: Header field name.
            default: Value to return if key is not found.

        Returns:
            The first header value string or default if not found.
        """
        lower_name: str = name.lower()
        if lower_name in self._store:
            _, values = self._store[lower_name]
            return values[0] if values else default
        return default

    def get_all(self, name: str) -> list[str]:
        """Get all values associated with a header name.

        Args:
            name: Header field name.

        Returns:
            List of all values for this header.
        """
        lower_name: str = name.lower()
        if lower_name in self._store:
            _, values = self._store[lower_name]
            return list(values)
        return []

    def remove(self, name: str) -> bool:
        """Remove all occurrences of a header name.

        Args:
            name: Header field name to remove.

        Returns:
            True if header was present and removed, False otherwise.
        """
        lower_name: str = name.lower()
        if lower_name in self._store:
            del self._store[lower_name]
            return True
        return False

    def contains(self, name: str) -> bool:
        """Check if header name is present.

        Args:
            name: Header field name.

        Returns:
            True if present.
        """
        return name.lower() in self._store

    def __getitem__(self, name: str) -> str:
        value = self.get(name)
        if value is None:
            raise KeyError(name)
        return value

    def __setitem__(self, name: str, value: str) -> None:
        self.set(name, value)

    def __delitem__(self, name: str) -> None:
        if not self.remove(name):
            raise KeyError(name)

    def __contains__(self, name: str) -> bool:
        return self.contains(name)

    def items(self) -> Iterator[tuple[str, str]]:
        """Iterate over all (original_name, value) pairs."""
        return iter(self)

    def __iter__(self) -> Iterator[tuple[str, str]]:
        """Iterate over all (original_name, value) pairs."""
        for _, (orig_name, values) in self._store.items():
            for val in values:
                yield (orig_name, val)

    def __len__(self) -> int:
        """Total count of header key-value pairs."""
        return sum(len(values) for _, values in self._store.values())

    def to_dict(self) -> dict[str, str]:
        """Convert headers to a standard dictionary (joining multi-values with comma).

        Returns:
            Dictionary mapping original header name to joined header values.
        """
        result: dict[str, str] = {}
        for _, (orig_name, values) in self._store.items():
            result[orig_name] = ", ".join(values)
        return result

    def copy(self) -> Headers:
        """Create a deep copy of this Headers instance.

        Returns:
            A new Headers object with cloned headers.
        """
        new_headers = Headers()
        for _, (orig_name, values) in self._store.items():
            new_headers._store[orig_name.lower()] = (orig_name, list(values))
        return new_headers
