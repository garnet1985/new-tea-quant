"""Tag catalog Facade 冒烟。"""

from __future__ import annotations

from unittest.mock import patch

from core.modules.tag import Tag


@patch.object(Tag, "fetch_catalog_page", return_value=([], 0, {"ok": True}))
def test_fetch_page_delegates(_mock):
    items, total, data_end = Tag.fetch_catalog_page(page=1, limit=10)
    assert items == []
    assert total == 0
    assert data_end.get("ok") is True
