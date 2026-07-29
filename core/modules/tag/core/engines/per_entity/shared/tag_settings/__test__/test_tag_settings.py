"""TagSettings 单元测试（新 core 包）。"""

from __future__ import annotations

import pytest

from core.modules.tag.core.engines.per_entity.shared.tag_settings import TagSettings

_STOCK_KLINE = {"data_key": "stock.kline.daily", "params": {"adjust": "qfq"}}


def _userspace_settings(**overrides) -> dict:
    base = {
        "is_enabled": True,
        "meta": {"key": "test_tag", "display_name": "test"},
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
            nested = dict(base.get(key) or {})
            nested.update(value)
            base[key] = nested
        else:
            base[key] = value
    return base


class TestTagSettings:
    def test_from_dict_expands_for_engine(self):
        raw = _userspace_settings(
            data={
                "base": _STOCK_KLINE,
                "required": [
                    {"data_key": "stock.indicators.daily", "params": {}},
                ],
                "min_required_records": 5,
            },
            calculation={
                "update_mode": "refresh",
                "recompute": True,
                "execution": {"mode": "entity_based"},
            },
        )
        ts = TagSettings.from_dict(raw, tag_key="demo/market_cap_tier")
        report = ts.validate()
        assert report.is_usable(), report.errors
        out = ts.to_dict()
        assert out["name"] == "demo/market_cap_tier"
        assert out["meta"]["key"] == "test_tag"
        assert out["execution_mode"] == "entity_based"
        assert out["recompute"] is True
        assert out["update_mode"] == "refresh"
        assert out["incremental_required_records_before_as_of_date"] == 5
        assert out["target_entity"] == {"type": "stock_kline_daily"}
        assert out["tag_target_type"] == "entity_based"
        assert out["data"]["tag_time_axis_based_on"] == "stock.kline.daily"
        assert [x["data_key"] for x in out["data"]["required"]] == [
            "stock.kline.daily",
            "stock.indicators.daily",
        ]

    def test_meta_key_fallback_to_tag_key(self):
        raw = _userspace_settings(meta={"display_name": "test"})
        # override clears key
        raw["meta"] = {"display_name": "test"}
        ts = TagSettings.from_dict(raw, tag_key="demo/market_cap_tier")
        report = ts.validate()
        assert report.is_usable(), report.errors
        assert ts.key == "demo/market_cap_tier"

    def test_meta_key_required_without_tag_key(self):
        raw = _userspace_settings()
        raw["meta"] = {"display_name": "test"}
        ts = TagSettings.from_dict(raw)
        report = ts.validate()
        assert not report.is_usable()
        assert any(e["field_path"] == "meta.key" for e in report.errors)

    def test_recompute_forces_refresh_update_mode(self):
        raw = _userspace_settings(
            calculation={
                "update_mode": "incremental",
                "recompute": True,
                "execution": {"mode": "entity_based"},
            }
        )
        ts = TagSettings.from_dict(raw, tag_key="demo/x")
        ts.apply_defaults()
        assert ts.update_mode == "refresh"

    def test_slice_based_allows_incremental(self):
        raw = _userspace_settings(
            calculation={
                "update_mode": "incremental",
                "recompute": False,
                "execution": {"mode": "slice_based"},
            }
        )
        ts = TagSettings.from_dict(raw, tag_key="demo/x")
        report = ts.validate()
        assert report.is_usable(), report.errors
        assert ts.update_mode == "incremental"

    def test_tag_definitions_required(self):
        raw = _userspace_settings()
        raw.pop("tag_definitions")
        ts = TagSettings.from_dict(raw, tag_key="demo/x")
        report = ts.validate()
        assert not report.is_usable()
        assert any(e["field_path"] == "tag_definitions" for e in report.errors)

    def test_is_dry_run_defaults_false(self):
        ts = TagSettings.from_dict(_userspace_settings(), tag_key="demo/x")
        ts.apply_defaults()
        assert ts.is_dry_run is False
        assert ts.to_dict()["is_dry_run"] is False
        assert ts.to_dict()["calculation"]["is_dry_run"] is False

    def test_is_dry_run_from_settings(self):
        raw = _userspace_settings(
            calculation={
                "update_mode": "incremental",
                "is_dry_run": True,
                "execution": {"mode": "entity_based"},
            }
        )
        ts = TagSettings.from_dict(raw, tag_key="demo/x")
        report = ts.validate()
        assert report.is_usable(), report.errors
        assert ts.is_dry_run is True
        assert ts.to_dict()["is_dry_run"] is True

    def test_global_base_macro_gdp_validates(self):
        raw = _userspace_settings(
            data={
                "base": {"data_key": "macro.gdp", "params": {}},
                "required": [],
                "min_required_records": 0,
            },
            calculation={
                "update_mode": "incremental",
                "execution": {"mode": "entity_based"},
            },
        )
        ts = TagSettings.from_dict(raw, tag_key="demo/macro_gdp")
        report = ts.validate()
        assert report.is_usable(), report.errors
        assert ts.data.base_route() == "global"
        assert any(
            w["field_path"] == "calculation.execution.mode" for w in report.warnings
        )
        assert ts.data.tag_time_axis_based_on == "macro.gdp"

    def test_global_base_without_mode_ok(self):
        raw = _userspace_settings(
            data={
                "base": {"data_key": "macro.cpi", "params": {}},
                "required": [],
                "min_required_records": 0,
            },
        )
        raw["calculation"] = {
            "update_mode": "incremental",
            "execution": {"start_date": "", "end_date": ""},
        }
        ts = TagSettings.from_dict(raw, tag_key="demo/macro_cpi")
        report = ts.validate()
        assert report.is_usable(), report.errors
        assert ts.data.base_route() == "global"
        assert not any(
            w["field_path"] == "calculation.execution.mode" for w in report.warnings
        )

    def test_non_time_series_base_ok(self):
        raw = _userspace_settings(
            data={
                "base": {"data_key": "stock.list", "params": {}},
                "required": [],
                "min_required_records": 0,
            },
        )
        raw["calculation"] = {
            "update_mode": "refresh",
            "recompute": True,
            "execution": {"start_date": "", "end_date": ""},
        }
        ts = TagSettings.from_dict(raw, tag_key="demo/list")
        report = ts.validate()
        assert report.is_usable(), report.errors
        assert ts.data.base_route() == "non_time_series"
        assert ts.data.tag_time_axis_based_on == ""

    def test_demo_market_cap_tier_settings(self):
        from userspace.extensions.tags.demo.market_cap_tier.settings import (
            settings as demo_settings,
        )

        ts = TagSettings.from_dict(demo_settings, tag_key="demo/market_cap_tier")
        report = ts.validate()
        assert report.is_usable(), report.errors
        assert ts.recompute is False
        assert ts.is_dry_run is False
        assert ts.update_mode == "incremental"
        assert ts.data.min_required_records == 1
        assert ts.attach_to_data_key == "stock.kline.daily"
        assert ts.target_entity_type == "stock_kline_daily"
