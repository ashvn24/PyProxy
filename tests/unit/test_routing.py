"""Unit tests for RouteRule and Router."""

from __future__ import annotations

import pytest

from pyproxy.exceptions import RouteNotFoundError
from pyproxy.protocol import HTTPRequest, Headers
from pyproxy.routing import RouteMatchType, RouteRule, Router


class TestRouteRule:
    """Tests for RouteRule pattern matching."""

    def test_prefix_matching(self):
        rule = RouteRule(path_pattern="/api", match_type=RouteMatchType.PREFIX)
        req1 = HTTPRequest(path="/api/v1/users")
        req2 = HTTPRequest(path="/api")
        req3 = HTTPRequest(path="/other")

        assert rule.matches(req1) is True
        assert rule.matches(req2) is True
        assert rule.matches(req3) is False

    def test_method_matching(self):
        rule = RouteRule(path_pattern="/api", methods={"POST", "PUT"})
        req_post = HTTPRequest(method="POST", path="/api")
        req_get = HTTPRequest(method="GET", path="/api")

        assert rule.matches(req_post) is True
        assert rule.matches(req_get) is False

    def test_host_matching(self):
        rule = RouteRule(path_pattern="/", host_pattern="api.example.com")
        req_valid = HTTPRequest(headers=Headers({"Host": "api.example.com"}))
        req_invalid = HTTPRequest(headers=Headers({"Host": "other.com"}))

        assert rule.matches(req_valid) is True
        assert rule.matches(req_invalid) is False

    def test_wildcard_host_matching(self):
        rule = RouteRule(path_pattern="/", host_pattern="*.example.com")
        req_valid = HTTPRequest(headers=Headers({"Host": "sub.example.com"}))
        assert rule.matches(req_valid) is True

    def test_regex_matching(self):
        rule = RouteRule(path_pattern=r"^/users/\d+$", match_type=RouteMatchType.REGEX)
        req_valid = HTTPRequest(path="/users/12345")
        req_invalid = HTTPRequest(path="/users/abc")

        assert rule.matches(req_valid) is True
        assert rule.matches(req_invalid) is False

    def test_strip_prefix(self):
        rule = RouteRule(path_pattern="/api/v1", strip_prefix=True)
        assert rule.rewrite_path("/api/v1/users/123") == "/users/123"


class TestRouter:
    """Tests for Router longest-prefix and priority dispatch."""

    def test_longest_prefix_priority(self):
        router = Router()
        rule_short = RouteRule(path_pattern="/api", priority=5)
        rule_long = RouteRule(path_pattern="/api/v1", priority=10)

        router.add_route(rule_short)
        router.add_route(rule_long)

        req = HTTPRequest(path="/api/v1/health")
        matched = router.match(req)

        assert matched is rule_long

    def test_unmatched_route_raises(self):
        router = Router()
        router.add_route(RouteRule(path_pattern="/api"))

        req = HTTPRequest(path="/unmatched")
        with pytest.raises(RouteNotFoundError):
            router.match(req)
