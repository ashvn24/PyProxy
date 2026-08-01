"""Lightweight dependency injection container.

Provides a simple, transparent DI container with three lifetime scopes:
- **Transient**: New instance created on every ``resolve()`` call.
- **Singleton**: One instance per container, lazily created.
- **Scoped**: One instance per scope (e.g., per HTTP request).

The container is ~120 lines of explicit code with no metaclass magic,
no decorators, and no auto-wiring. Dependencies are registered and resolved
explicitly, making the wiring fully traceable.

Example::

    container = Container()
    container.register_singleton(ConfigLoader, lambda: ConfigLoader(Path("config.yaml")))

    loader = container.resolve(ConfigLoader)  # Creates and caches the instance
    same_loader = container.resolve(ConfigLoader)  # Returns the cached instance
    assert loader is same_loader
"""

from __future__ import annotations

import enum
import threading
from typing import Any, TypeVar

T = TypeVar("T")


class Lifetime(enum.Enum):
    """Lifetime scope for registered dependencies.

    Attributes:
        TRANSIENT: New instance created on every resolution.
        SINGLETON: Single instance shared across the container's lifetime.
        SCOPED: Single instance per scope (created via ``create_scope()``).
    """

    TRANSIENT = "transient"
    SINGLETON = "singleton"
    SCOPED = "scoped"


class _Registration:
    """Internal record of a registered dependency.

    Attributes:
        factory: Callable that creates the dependency instance.
        lifetime: The lifetime scope of the registration.
        instance: Cached instance for singleton registrations.
    """

    __slots__ = ("factory", "instance", "lifetime")

    def __init__(self, factory: Any, lifetime: Lifetime) -> None:
        self.factory = factory
        self.lifetime = lifetime
        self.instance: Any = None


class Container:
    """A lightweight, type-safe dependency injection container.

    Supports transient, singleton, and scoped lifetimes. All operations
    are thread-safe for use in multi-threaded contexts (e.g., signal handlers).

    Example::

        container = Container()

        # Register a singleton
        container.register_singleton(Database, lambda: Database("connection_string"))

        # Register a transient (new instance each time)
        container.register(RequestHandler, lambda: RequestHandler())

        # Resolve
        db = container.resolve(Database)
    """

    def __init__(self) -> None:
        """Initialize an empty container."""
        self._registrations: dict[type[Any], _Registration] = {}
        self._lock = threading.Lock()
        self._scoped_instances: dict[type[Any], Any] = {}
        self._parent: Container | None = None

    def register(
        self,
        interface: type[T],
        factory: Any,
        lifetime: Lifetime = Lifetime.TRANSIENT,
    ) -> None:
        """Register a dependency with the specified lifetime.

        Args:
            interface: The type/interface to register. Used as the lookup key
                when resolving.
            factory: A callable that creates an instance of the dependency.
                Called with no arguments.
            lifetime: The lifetime scope for this registration.

        Raises:
            TypeError: If ``interface`` is not a type or ``factory`` is not callable.
        """
        if not isinstance(interface, type):
            raise TypeError(f"interface must be a type, got {type(interface).__name__}")
        if not callable(factory):
            raise TypeError(f"factory must be callable, got {type(factory).__name__}")

        with self._lock:
            self._registrations[interface] = _Registration(factory, lifetime)

    def register_singleton(self, interface: type[T], factory: Any) -> None:
        """Register a singleton dependency.

        Convenience method equivalent to ``register(interface, factory, Lifetime.SINGLETON)``.

        Args:
            interface: The type/interface to register.
            factory: A callable that creates the singleton instance.
        """
        self.register(interface, factory, Lifetime.SINGLETON)

    def register_scoped(self, interface: type[T], factory: Any) -> None:
        """Register a scoped dependency.

        Scoped dependencies have one instance per scope. Scopes are created
        via :meth:`create_scope`.

        Args:
            interface: The type/interface to register.
            factory: A callable that creates the scoped instance.
        """
        self.register(interface, factory, Lifetime.SCOPED)

    def register_instance(self, interface: type[T], instance: T) -> None:
        """Register a pre-created instance as a singleton.

        Useful for registering configuration objects or other pre-built
        dependencies.

        Args:
            interface: The type/interface to register.
            instance: The pre-created instance to register.
        """
        if not isinstance(interface, type):
            raise TypeError(f"interface must be a type, got {type(interface).__name__}")

        with self._lock:
            registration = _Registration(lambda: instance, Lifetime.SINGLETON)
            registration.instance = instance
            self._registrations[interface] = registration

    def resolve(self, interface: type[T]) -> T:
        """Resolve a dependency by its registered type.

        Args:
            interface: The type/interface to resolve.

        Returns:
            An instance of the requested type, following the lifetime rules.

        Raises:
            KeyError: If the type has not been registered.
        """
        with self._lock:
            registration = self._find_registration(interface)

            if registration.lifetime == Lifetime.SINGLETON:
                if registration.instance is None:
                    registration.instance = registration.factory()
                return registration.instance  # type: ignore[no-any-return]

            if registration.lifetime == Lifetime.SCOPED:
                if interface in self._scoped_instances:
                    return self._scoped_instances[interface]  # type: ignore[no-any-return]
                instance = registration.factory()
                self._scoped_instances[interface] = instance
                return instance  # type: ignore[no-any-return]

            # Transient — always create a new instance
            return registration.factory()  # type: ignore[no-any-return]

    def is_registered(self, interface: type[Any]) -> bool:
        """Check if a type is registered in this container or its parent.

        Args:
            interface: The type to check.

        Returns:
            True if the type is registered.
        """
        with self._lock:
            if interface in self._registrations:
                return True
            if self._parent is not None:
                return self._parent.is_registered(interface)
            return False

    def create_scope(self) -> Container:
        """Create a child container scope.

        The child scope inherits all registrations from the parent but
        maintains its own scoped instance cache. Useful for per-request
        dependency scoping.

        Returns:
            A new Container that is a child of this one.
        """
        scope = Container()
        scope._parent = self
        return scope

    def _find_registration(self, interface: type[Any]) -> _Registration:
        """Find a registration in this container or its parent chain.

        Args:
            interface: The type to find.

        Returns:
            The registration record.

        Raises:
            KeyError: If the type is not registered anywhere in the chain.
        """
        if interface in self._registrations:
            return self._registrations[interface]
        if self._parent is not None:
            return self._parent._find_registration(interface)
        raise KeyError(
            f"No registration found for {interface.__name__}. "
            f"Did you forget to call container.register({interface.__name__}, ...)?"
        )

    def clear(self) -> None:
        """Remove all registrations and cached instances.

        Primarily used in tests to reset the container state.
        """
        with self._lock:
            self._registrations.clear()
            self._scoped_instances.clear()
