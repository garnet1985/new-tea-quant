"""settings 校验。"""

from __future__ import annotations

import pytest

from core.modules.series_relation.core.constants import MAX_SERIES
from core.modules.series_relation.core.settings.relation_settings import validate_settings

pytestmark = pytest.mark.force_run


def _lookup(key: str):
    catalog = {
        "macro.lpr": {"meta": {"type": "time_series", "scope": "global"}},
        "stock.kline.daily": {"meta": {"type": "time_series", "scope": "per_entity"}},
        "stock.list": {"meta": {"type": "snapshot", "scope": "global"}},
    }
    return catalog.get(key)


def test_validate_ok() -> None:
    raw = {
        "meta": {"key": "demo", "display_name": "Demo"},
        "series": [
            {"data_key": "macro.lpr", "field": "lpr_1y"},
            {
                "data_key": "stock.kline.daily",
                "entity_id": "000300.SH",
                "field": "close",
            },
        ],
        "normalize": "zscore",
    }
    settings, errors = validate_settings(raw, declaration_lookup=_lookup)
    assert errors == []
    assert settings is not None
    assert settings["series"][0]["scope"] == "global"
    assert settings["series"][1]["entity_id"] == "000300.SH"


def test_reject_max_series_in_settings_and_over_limit() -> None:
    raw = {
        "meta": {"key": "x"},
        "series": [{"data_key": "macro.lpr", "field": "lpr_1y"}],
        "max_series": 3,
    }
    _, errors = validate_settings(raw, declaration_lookup=_lookup)
    assert any("max_series" in e for e in errors)

    too_many = {
        "meta": {"key": "x"},
        "series": [
            {"data_key": "macro.lpr", "field": f"f{i}"} for i in range(MAX_SERIES + 1)
        ],
    }
    _, errors2 = validate_settings(too_many, declaration_lookup=_lookup)
    assert any("最多" in e for e in errors2)


def test_per_entity_requires_entity() -> None:
    raw = {
        "meta": {"key": "x"},
        "series": [{"data_key": "stock.kline.daily", "field": "close"}],
    }
    _, errors = validate_settings(raw, declaration_lookup=_lookup)
    assert any("entity_id" in e for e in errors)
