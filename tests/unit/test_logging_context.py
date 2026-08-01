"""Tests for contextvars-based logging context."""

from __future__ import annotations

import asyncio

import pytest

from pyproxy.logging.context import (
    RequestContext,
    get_correlation_id,
    get_extra_context,
    get_request_id,
    set_correlation_id,
    set_request_id,
)


class TestContextVars:
    """Tests for individual context variable setters/getters."""

    def test_default_request_id_empty(self):
        assert get_request_id() == ""

    def test_set_get_request_id(self):
        token = set_request_id("req-123")
        assert get_request_id() == "req-123"
        # Cleanup: reset via the token's context var
        from pyproxy.logging.context import _request_id_var
        _request_id_var.reset(token)

    def test_default_correlation_id_empty(self):
        assert get_correlation_id() == ""

    def test_set_get_correlation_id(self):
        token = set_correlation_id("corr-456")
        assert get_correlation_id() == "corr-456"
        from pyproxy.logging.context import _correlation_id_var
        _correlation_id_var.reset(token)


class TestRequestContext:
    """Tests for the RequestContext context manager."""

    def test_sync_context_sets_values(self):
        with RequestContext(request_id="req-abc", correlation_id="corr-xyz"):
            assert get_request_id() == "req-abc"
            assert get_correlation_id() == "corr-xyz"
        # Values should be restored after exit
        assert get_request_id() == ""
        assert get_correlation_id() == ""

    def test_sync_context_restores_previous(self):
        token = set_request_id("outer")
        with RequestContext(request_id="inner"):
            assert get_request_id() == "inner"
        assert get_request_id() == "outer"
        from pyproxy.logging.context import _request_id_var
        _request_id_var.reset(token)

    def test_nested_contexts(self):
        with RequestContext(request_id="outer", correlation_id="corr-outer"):
            assert get_request_id() == "outer"
            with RequestContext(request_id="inner", correlation_id="corr-inner"):
                assert get_request_id() == "inner"
                assert get_correlation_id() == "corr-inner"
            assert get_request_id() == "outer"
            assert get_correlation_id() == "corr-outer"
        assert get_request_id() == ""

    def test_extra_context(self):
        with RequestContext(extra={"user_id": "u-123"}):
            assert get_extra_context() == {"user_id": "u-123"}
        assert get_extra_context() == {}

    def test_context_restores_on_exception(self):
        try:
            with RequestContext(request_id="req-err"):
                assert get_request_id() == "req-err"
                raise ValueError("test error")
        except ValueError:
            pass
        assert get_request_id() == ""


class TestAsyncRequestContext:
    """Tests for async RequestContext behavior."""

    @pytest.mark.asyncio
    async def test_async_context_sets_values(self):
        async with RequestContext(request_id="async-req"):
            assert get_request_id() == "async-req"
        assert get_request_id() == ""

    @pytest.mark.asyncio
    async def test_async_context_isolation(self):
        """Context set in one task does not leak to another."""
        results = {}

        async def task_a():
            async with RequestContext(request_id="task-a"):
                await asyncio.sleep(0.01)
                results["a"] = get_request_id()

        async def task_b():
            async with RequestContext(request_id="task-b"):
                await asyncio.sleep(0.01)
                results["b"] = get_request_id()

        await asyncio.gather(task_a(), task_b())

        assert results["a"] == "task-a"
        assert results["b"] == "task-b"
        assert get_request_id() == ""

    @pytest.mark.asyncio
    async def test_async_context_restores_on_exception(self):
        try:
            async with RequestContext(request_id="async-err"):
                raise ValueError("async error")
        except ValueError:
            pass
        assert get_request_id() == ""
