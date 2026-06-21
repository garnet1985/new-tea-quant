"""Tests for data source catalog launcher."""

from __future__ import annotations

from core.modules.data_source.catalog.provider_probe import (
    min_rate_limit_per_minute,
    probe_provider_auth_configured,
    resolve_api_rate_limit_per_minute,
    summarize_provider_auth,
)
from core.modules.data_source.launcher import (
    fetch_data_source_catalog_page,
    fetch_data_source_freshness,
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


def test_fetch_catalog_page_shape():
    items, total, data_end = fetch_data_source_catalog_page(page=1, limit=500)
    assert total >= len(items)
    assert isinstance(data_end, dict)
    assert "is_end_date_truncated" in data_end
    if data_end.get("is_end_date_truncated"):
        assert data_end.get("truncation_settings_path") == "/settings/data"
    if not items:
        return
    row = items[0]
    assert row["name"]
    assert row["display_name"]
    assert "providers" in row
    assert "renew_type" in row
    assert "renew_type_label" in row
    assert "renew_interval_days" in row
    assert "rate_limit_per_minute" in row
    assert "requires_auth" in row
    assert "auth_ready" in row
    assert "can_renew" in row
    assert "update_status" not in row
    assert row["origin"] in ("system", "userspace")
    assert isinstance(row["is_custom"], bool)

    stock_list = next((i for i in items if i["name"] == "stock_list"), None)
    if stock_list:
        assert stock_list["display_name"] == "股票列表"
        assert stock_list["origin"] == "system"
        assert stock_list["renew_type_label"] in ("增量", "滚动", "全量刷新")


def test_fetch_freshness_shape():
    items, data_end = fetch_data_source_freshness()
    assert isinstance(items, dict)
    assert isinstance(data_end, dict)
    assert "is_end_date_truncated" in data_end
    if not items:
        return
    name, status = next(iter(items.items()))
    assert name
    assert status["update_status"] in ("needs_update", "up_to_date")
    assert status["update_status_label"] in ("需要更新", "已经更新")
