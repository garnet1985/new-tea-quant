"""Tests for tag catalog launcher."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from core.modules.tag.launcher.tag_catalog import _compute_status, fetch_discovered_tags_page


def test_compute_status_needs_recompute_when_behind_effective_end():
    hint = "data.json 已截断"
    status, label, out_hint = _compute_status("20250601", "20251231", hint)
    assert status == "needs_recompute"
    assert label == "需要计算"
    assert out_hint == hint


def test_compute_status_up_to_date_when_caught_up():
    status, label, hint = _compute_status("20251231", "20251231", "ignored")
    assert status == "up_to_date"
    assert label == "已经更新"
    assert hint == ""


@patch("core.modules.tag.launcher.tag_catalog.TagDiscoveryHelper.discover_tags", return_value={})
def test_fetch_discovered_tags_page_empty_returns_data_end(_mock_discover):
    items, total, data_end = fetch_discovered_tags_page(page=1, limit=10)
    assert items == []
    assert total == 0
    assert isinstance(data_end, dict)
