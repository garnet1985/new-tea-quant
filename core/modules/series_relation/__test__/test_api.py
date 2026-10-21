"""公开 Facade 冒烟。"""

from __future__ import annotations

import pytest

from core.modules.series_relation import SeriesRelation
from core.modules.series_relation.contracts import DiscoveredRelation

pytestmark = pytest.mark.force_run


def test_facade_exports() -> None:
    assert SeriesRelation.MAX_SERIES >= 1
    assert callable(SeriesRelation.list_infos)
    assert callable(SeriesRelation.run)
    assert DiscoveredRelation is not None


def test_validate_via_facade(monkeypatch: pytest.MonkeyPatch) -> None:
    def _lookup_factory():
        catalog = {
            "macro.lpr": {"meta": {"type": "time_series", "scope": "global"}}
        }
        return catalog.get

    monkeypatch.setattr(
        SeriesRelation, "_declaration_lookup", staticmethod(_lookup_factory)
    )
    report = SeriesRelation.validate(
        {
            "meta": {"key": "x"},
            "series": [{"data_key": "macro.lpr", "field": "lpr_1y"}],
        }
    )
    assert report["ok"] is True
