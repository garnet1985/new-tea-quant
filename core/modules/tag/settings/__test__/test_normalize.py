"""Tag settings normalize 单元测试。"""
from __future__ import annotations

import pytest

from core.modules.tag.models.scenario_model import ScenarioModel
from core.modules.tag.settings.normalize import normalize_tag_settings

_STOCK_KLINE = {"data_key": "stock.kline.daily", "params": {"adjust": "qfq"}}


def _userspace_settings(**overrides) -> dict:
    base = {
        "is_enabled": True,
        "meta": {"display_name": "test"},
        "calculation": {
            "update_mode": "incremental",
            "execution": {"mode": "entity_based"},
        },
        "data": {
            "base": _STOCK_KLINE,
            "required": [],
            "min_required_records": 0,
        },
        "tag_definitions": [{"name": "tag1"}],
    }
    for key, value in overrides.items():
        if key in ("calculation", "data", "meta") and isinstance(value, dict):
            base[key] = {**base.get(key, {}), **value}
        else:
            base[key] = value
    return base


class TestNormalizeTagSettings:
    def test_expands_calculation_and_data(self):
        raw = _userspace_settings(
            data={
                "base": _STOCK_KLINE,
                "required": [
                    {"data_key": "stock.indicators.daily", "params": {}},
                ],
                "min_required_records": 5,
            },
            calculation={"update_mode": "refresh", "recompute": True},
        )
        norm = normalize_tag_settings(raw, tag_key="demo/market_cap_tier")
        assert norm["name"] == "demo/market_cap_tier"
        assert norm["execution_mode"] == "entity_based"
        assert norm["recompute"] is True
        assert norm["update_mode"] == "refresh"
        assert norm["incremental_required_records_before_as_of_date"] == 5
        assert norm["target_entity"] == {"type": "stock_kline_daily"}
        assert norm["tag_target_type"] == "entity_based"
        assert norm["data"]["tag_time_axis_based_on"] == "stock.kline.daily"
        assert [x["data_key"] for x in norm["data"]["required"]] == [
            "stock.kline.daily",
            "stock.indicators.daily",
        ]
        assert ScenarioModel.is_setting_valid(norm) is True

    def test_meta_key_preserved(self):
        raw = _userspace_settings(meta={"key": "cap_tier", "display_name": "test"})
        norm = normalize_tag_settings(raw, tag_key="demo/market_cap_tier")
        assert norm["meta"]["key"] == "cap_tier"

    def test_market_cap_tier_settings(self):
        from userspace.extensions.tags.demo.market_cap_tier.settings import settings as demo_settings

        norm = normalize_tag_settings(demo_settings, tag_key="demo/market_cap_tier")
        assert norm["update_mode"] == "incremental"
        assert norm["incremental_required_records_before_as_of_date"] == 1
        scenario = ScenarioModel.create_from_settings(demo_settings, tag_key="demo/market_cap_tier")
        assert scenario is not None
        assert scenario.get_target_entity() == "stock_kline_daily"

    def test_rejects_missing_base(self):
        with pytest.raises(ValueError, match="data 须为 dict"):
            normalize_tag_settings({"tag_definitions": [{"name": "t"}]}, tag_key="x")
