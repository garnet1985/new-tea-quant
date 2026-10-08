"""Tests for data source catalog (BFF helpers)."""

from __future__ import annotations

from core.bff.APIs.data.sources.helpers.source_catalog import (
    fetch_data_source_catalog_page,
    fetch_data_source_freshness,
)


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
