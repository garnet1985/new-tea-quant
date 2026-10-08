"""Provider 鉴权与限速探测。"""
from __future__ import annotations

from core.modules.data_source.core.catalog.provider_probe import (
    min_rate_limit_per_minute,
    probe_provider_auth_configured,
    resolve_api_rate_limit_per_minute,
    summarize_provider_auth,
)


class _FakeProvider:
    provider_name = "fake_paid"
    requires_auth = True
    auth_type = "token"
    api_limits = {"get_data": 500, "get_meta": 200}
    default_rate_limit = 60


class _FakeFreeProvider:
    provider_name = "fake_free"
    requires_auth = False
    auth_type = None
    api_limits = {"get_data": 80}
    default_rate_limit = 80


class _FakeApi:
    def __init__(self, provider_name: str, method: str):
        self.provider_name = provider_name
        self.method = method


def test_resolve_api_rate_limit_uses_minimum_method_limit():
    limit = resolve_api_rate_limit_per_minute(_FakeProvider, "get_meta")
    assert limit == 200


def test_min_rate_limit_across_apis():
    apis = {
        "a": _FakeApi("fake_paid", "get_data"),
        "b": _FakeApi("fake_paid", "get_meta"),
    }
    assert min_rate_limit_per_minute(apis, {"fake_paid": _FakeProvider}) == 200


def test_summarize_provider_auth_when_free_only():
    auth = summarize_provider_auth(["fake_free"], {"fake_free": _FakeFreeProvider})
    assert auth["requires_auth"] is False
    assert auth["auth_ready"] is True


def test_probe_provider_auth_free_provider():
    assert probe_provider_auth_configured(_FakeFreeProvider) is True
