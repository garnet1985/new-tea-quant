"""DataSource catalog Facade smoke."""

from __future__ import annotations

from core.modules.data_source import DataSourceManager


def test_fetch_catalog_page_shape():
    items, total, data_end = DataSourceManager.fetch_catalog_page(page=1, limit=500)
    assert total >= len(items)
    assert isinstance(data_end, dict)
    assert "is_end_date_truncated" in data_end
    if data_end.get("is_end_date_truncated"):
        assert data_end.get("truncation_settings_path") == "/settings/membership"
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
