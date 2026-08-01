"""Tests for the dependency injection container."""

from __future__ import annotations

import pytest

from pyproxy.core.container import Container, Lifetime


class FakeService:
    """A fake service for testing."""

    def __init__(self, value: str = "default") -> None:
        self.value = value


class AnotherService:
    """Another fake service for testing."""
    pass


class TestContainerRegistration:
    """Tests for dependency registration."""

    def test_register_and_resolve(self, container):
        container.register(FakeService, lambda: FakeService("test"))
        result = container.resolve(FakeService)
        assert isinstance(result, FakeService)
        assert result.value == "test"

    def test_register_non_type_raises(self, container):
        with pytest.raises(TypeError, match="interface must be a type"):
            container.register("not_a_type", lambda: None)  # type: ignore[arg-type]

    def test_register_non_callable_raises(self, container):
        with pytest.raises(TypeError, match="factory must be callable"):
            container.register(FakeService, "not_callable")  # type: ignore[arg-type]

    def test_resolve_unregistered_raises(self, container):
        with pytest.raises(KeyError, match="No registration found"):
            container.resolve(FakeService)

    def test_is_registered_true(self, container):
        container.register(FakeService, lambda: FakeService())
        assert container.is_registered(FakeService) is True

    def test_is_registered_false(self, container):
        assert container.is_registered(FakeService) is False


class TestTransientLifetime:
    """Tests for transient (new instance per resolve) lifetime."""

    def test_transient_creates_new_instances(self, container):
        container.register(FakeService, lambda: FakeService(), Lifetime.TRANSIENT)
        instance1 = container.resolve(FakeService)
        instance2 = container.resolve(FakeService)
        assert instance1 is not instance2

    def test_default_lifetime_is_transient(self, container):
        container.register(FakeService, lambda: FakeService())
        instance1 = container.resolve(FakeService)
        instance2 = container.resolve(FakeService)
        assert instance1 is not instance2


class TestSingletonLifetime:
    """Tests for singleton (one instance per container) lifetime."""

    def test_singleton_returns_same_instance(self, container):
        container.register_singleton(FakeService, lambda: FakeService("single"))
        instance1 = container.resolve(FakeService)
        instance2 = container.resolve(FakeService)
        assert instance1 is instance2
        assert instance1.value == "single"

    def test_singleton_lazy_creation(self, container):
        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return FakeService()

        container.register_singleton(FakeService, factory)
        assert call_count == 0  # Not created yet
        container.resolve(FakeService)
        assert call_count == 1
        container.resolve(FakeService)
        assert call_count == 1  # Still only created once


class TestRegisterInstance:
    """Tests for pre-created instance registration."""

    def test_register_instance(self, container):
        instance = FakeService("pre-built")
        container.register_instance(FakeService, instance)
        resolved = container.resolve(FakeService)
        assert resolved is instance
        assert resolved.value == "pre-built"

    def test_register_instance_non_type_raises(self, container):
        with pytest.raises(TypeError):
            container.register_instance("not_type", FakeService())  # type: ignore[arg-type]


class TestScopedLifetime:
    """Tests for scoped (one instance per scope) lifetime."""

    def test_scoped_same_within_scope(self, container):
        container.register_scoped(FakeService, lambda: FakeService())
        scope = container.create_scope()
        instance1 = scope.resolve(FakeService)
        instance2 = scope.resolve(FakeService)
        assert instance1 is instance2

    def test_scoped_different_across_scopes(self, container):
        container.register_scoped(FakeService, lambda: FakeService())
        scope1 = container.create_scope()
        scope2 = container.create_scope()
        instance1 = scope1.resolve(FakeService)
        instance2 = scope2.resolve(FakeService)
        assert instance1 is not instance2


class TestChildScope:
    """Tests for parent-child container scope relationships."""

    def test_child_inherits_parent_registrations(self, container):
        container.register_singleton(FakeService, lambda: FakeService("parent"))
        child = container.create_scope()
        resolved = child.resolve(FakeService)
        assert resolved.value == "parent"

    def test_child_is_registered_checks_parent(self, container):
        container.register(FakeService, lambda: FakeService())
        child = container.create_scope()
        assert child.is_registered(FakeService) is True

    def test_child_unregistered_type(self, container):
        child = container.create_scope()
        with pytest.raises(KeyError):
            child.resolve(FakeService)


class TestContainerClear:
    """Tests for container clear/reset."""

    def test_clear_removes_registrations(self, container):
        container.register(FakeService, lambda: FakeService())
        container.clear()
        assert container.is_registered(FakeService) is False

    def test_clear_removes_singletons(self, container):
        container.register_singleton(FakeService, lambda: FakeService("v1"))
        instance1 = container.resolve(FakeService)

        container.clear()
        container.register_singleton(FakeService, lambda: FakeService("v2"))
        instance2 = container.resolve(FakeService)

        assert instance1 is not instance2
        assert instance2.value == "v2"


class TestMultipleRegistrations:
    """Tests for registering multiple services."""

    def test_multiple_services(self, container):
        container.register(FakeService, lambda: FakeService("fake"))
        container.register(AnotherService, lambda: AnotherService())

        fake = container.resolve(FakeService)
        another = container.resolve(AnotherService)

        assert isinstance(fake, FakeService)
        assert isinstance(another, AnotherService)

    def test_override_registration(self, container):
        container.register(FakeService, lambda: FakeService("v1"))
        container.register(FakeService, lambda: FakeService("v2"))
        result = container.resolve(FakeService)
        assert result.value == "v2"
