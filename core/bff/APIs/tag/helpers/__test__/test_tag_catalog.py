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


def test_last_computed_as_of_uses_calc_progress_min_not_max_as_of():
    class _Tags:
        def get_entity_calc_progress(self, _name: str):
            return {"__global__": "20251231", "extra": "20250620"}

        def get_max_as_of_date(self, _ids):
            raise AssertionError("must not use max(as_of) when progress exists")

        def load_scenario(self, _name: str):
            raise AssertionError("must not load scenario when progress exists")

    assert TagCatalog._last_computed_as_of("demo/macro_rate_stance", _Tags()) == "20250620"


def test_last_computed_as_of_none_when_progress_empty():
    class _Tags:
        def get_entity_calc_progress(self, _name: str):
            return {}

        def load_scenario(self, _name: str):
            return None

    assert TagCatalog._last_computed_as_of("demo/macro_rate_stance", _Tags()) is None


def test_last_computed_as_of_falls_back_to_max_as_of_when_no_progress():
    class _Tags:
        def get_entity_calc_progress(self, _name: str):
            return {}

        def load_scenario(self, _name: str):
            return {"id": 3}

        def get_tag_definitions(self, _sid: int):
            return [{"id": 9}]

        def get_max_as_of_date(self, ids):
            assert ids == [9]
            return "20260101"

    assert (
        TagCatalog._last_computed_as_of("demo/stock_area_cluster", _Tags())
        == "20260101"
    )


def test_summary_clamps_last_computed_to_effective_end():
    class _Tags:
        def get_entity_calc_progress(self, _name: str):
            return {"__global__": "20260101"}

        def load_scenario(self, _name: str):
            return {"id": 1, "updated_at": None}

        def get_tag_definitions(self, _sid: int):
            return [{"id": 1}]

    from unittest.mock import MagicMock

    item = MagicMock()
    item.id.return_value = "demo/macro_rate_stance"
    item.settings = {
        "is_enabled": True,
        "meta": {"display_name": "宏观", "description": ""},
        "tag_definitions": [{"name": "x", "display_name": "X"}],
        "calculation": {"update_mode": "incremental", "execution": {"mode": ""}},
    }
    row = TagCatalog._summary(
        item,
        _Tags(),
        effective_end="20251231",
        truncation_hint="truncated",
    )
    assert row["last_computed_as_of"] == "20251231"
    assert row["compute_status"] == "up_to_date"
    assert row["compute_status_label"] == "已经更新"


@patch(
    "core.bff.APIs.tag.helpers.tag_catalog.DiscoveryService.discover_tags",
    return_value=[],
)
def test_fetch_discovered_tags_page_empty_returns_data_end(_mock_discover):
    items, total, data_end = TagCatalog.fetch_page(page=1, limit=10)
    assert items == []
    assert total == 0
    assert isinstance(data_end, dict)
