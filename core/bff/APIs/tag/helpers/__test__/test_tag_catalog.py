"""Tests for tag catalog (BFF helpers)."""

from __future__ import annotations

from unittest.mock import patch

from core.bff.APIs.tag.helpers.tag_catalog import TagCatalog


def test_compute_status_needs_recompute_when_behind_effective_end():
    hint = "data.json 已截断"
    status, label, out_hint = TagCatalog._compute_status(
        "20250601", "20251231", hint
    )
    assert status == "needs_recompute"
    assert label == "需要更新"
    assert out_hint == hint


def test_compute_status_up_to_date_when_caught_up():
    status, label, hint = TagCatalog._compute_status(
        "20251231", "20251231", "ignored"
    )
    assert status == "up_to_date"
    assert label == "已经更新"
    assert hint == ""


@patch(
    "core.bff.APIs.tag.helpers.tag_catalog.DiscoveryService.discover_tags",
    return_value=[],
)
def test_fetch_discovered_tags_page_empty_returns_data_end(_mock_discover):
    items, total, data_end = TagCatalog.fetch_page(page=1, limit=10)
    assert items == []
    assert total == 0
    assert isinstance(data_end, dict)
