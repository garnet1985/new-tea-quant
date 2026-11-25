"""SeriesRelation BFF helper — Facade only."""

from __future__ import annotations

import pytest

from core.bff.APIs.series_relation.helpers.scenes import SeriesRelationScenes

pytestmark = pytest.mark.force_run


def test_list_items_smoke() -> None:
    items = SeriesRelationScenes.list_items()
    assert isinstance(items, list)
    if items:
        assert "key" in items[0]
        assert "display_name" in items[0]
