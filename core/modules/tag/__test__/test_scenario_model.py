"""ScenarioModel 单元测试。"""
from __future__ import annotations

import pytest

from core.modules.tag.enums import TagUpdateMode
from core.modules.tag.models.scenario_model import ScenarioModel
from core.modules.tag.settings.normalize import normalize_tag_settings

_STOCK_KLINE = {"data_id": "stock.kline.daily", "params": {"adjust": "qfq"}}


def _stock_scenario(**overrides) -> dict:
    base = {
        "is_enabled": True,
        "meta": {"display_name": "test_scenario"},
        "calculation": {
            "update_mode": "incremental",
            "execution_mode": "entity_timeline",
        },
        "data": {
            "base_required_data": _STOCK_KLINE,
            "extra_required_data_sources": [],
            "min_required_records": 10,
        },
        "tags": [{"name": "tag1"}],
    }
    for key, value in overrides.items():
        if key in ("calculation", "data", "meta") and isinstance(value, dict):
            base[key] = {**base.get(key, {}), **value}
        else:
            base[key] = value
    return base


def _normalized(**overrides) -> dict:
    return normalize_tag_settings(_stock_scenario(**overrides), tag_key="test_scenario")


class TestScenarioModel:
    def test_create_from_settings(self):
        scenario = ScenarioModel.create_from_settings(
            _stock_scenario(
                meta={
                    "display_name": "Test Scenario Display",
                    "description": "Test description",
                },
                tags=[
                    {"name": "tag1", "display_name": "Tag 1"},
                    {"name": "tag2", "display_name": "Tag 2"},
                ],
            ),
            tag_key="test_scenario",
        )
        assert scenario.name == "test_scenario"
        assert scenario.get_target_entity() == "stock_kline_daily"
        assert scenario.is_enabled() is True
        assert scenario.display_name == "Test Scenario Display"
        assert scenario.description == "Test description"
        assert [t.get_name() for t in scenario.get_tag_models()] == ["tag1", "tag2"]

        default = ScenarioModel.create_from_settings(
            _stock_scenario(), tag_key="test_scenario"
        )
        assert default.display_name == "test_scenario"

    def test_meta_display_name_without_name_in_userspace(self):
        raw = _stock_scenario(
            meta={"display_name": "From Meta", "description": "Meta desc"},
            data={"min_required_records": 0},
        )
        scenario = ScenarioModel.create_from_settings(raw, tag_key="demo/my_tag")
        assert scenario.name == "demo/my_tag"
        assert scenario.display_name == "From Meta"
        assert scenario.description == "Meta desc"

    def test_create_from_settings_rejects_invalid_base(self):
        assert ScenarioModel.create_from_settings(
            {
                "is_enabled": True,
                "data": {"base_required_data": {"data_id": "stock.list", "params": {}}},
                "tags": [{"name": "tag1"}],
            },
            tag_key="bad",
        ) is None

    @pytest.mark.parametrize(
        "raw,expected",
        [
            (_stock_scenario(), True),
            (
                {
                    "is_enabled": True,
                    "data": {
                        "base_required_data": _STOCK_KLINE,
                        "min_required_records": 0,
                    },
                    "tags": [{"name": "tag1"}],
                },
                True,
            ),
            (_stock_scenario(tags=[]), False),
            (
                _stock_scenario(data={"min_required_records": -1}),
                False,
            ),
            (
                {
                    "is_enabled": True,
                    "tags": [{"name": "tag1"}],
                },
                False,
            ),
        ],
    )
    def test_is_setting_valid(self, raw, expected):
        try:
            normalized = normalize_tag_settings(raw, tag_key="test_scenario")
        except ValueError:
            assert expected is False
            return
        assert ScenarioModel.is_setting_valid(normalized) is expected

    @pytest.mark.parametrize(
        "calc_overrides,expected",
        [
            ({"update_mode": "incremental"}, TagUpdateMode.INCREMENTAL),
            ({"update_mode": "refresh"}, TagUpdateMode.REFRESH),
            ({}, TagUpdateMode.INCREMENTAL),
        ],
    )
    def test_calculate_update_mode(self, calc_overrides, expected):
        scenario = ScenarioModel.create_from_settings(
            _stock_scenario(calculation=calc_overrides),
            tag_key="test_scenario",
        )
        assert scenario.calculate_update_mode() == expected

    def test_recompute_forces_refresh(self):
        scenario = ScenarioModel.create_from_settings(
            _stock_scenario(calculation={"recompute": True}),
            tag_key="test_scenario",
        )
        assert scenario.should_recompute() is True
        assert scenario.calculate_update_mode() == TagUpdateMode.REFRESH

    def test_calendar_slice_execution_mode(self):
        raw = _stock_scenario(
            calculation={
                "execution_mode": "calendar_slice",
                "recompute": True,
                "update_mode": "refresh",
            },
            data={"min_required_records": 20},
        )
        norm = normalize_tag_settings(raw, tag_key="slice_scenario")
        assert ScenarioModel.is_setting_valid(norm) is True
        scenario = ScenarioModel.create_from_settings(raw, tag_key="slice_scenario")
        assert scenario.get_execution_mode().value == "calendar_slice"

    def test_get_execution_mode(self):
        scenario = ScenarioModel.create_from_settings(
            _stock_scenario(), tag_key="test_scenario"
        )
        assert scenario.get_execution_mode().value == "entity_timeline"

    def test_get_tags_dict_and_to_dict(self):
        scenario = ScenarioModel.create_from_settings(
            _stock_scenario(
                meta={"display_name": "Test Scenario", "description": "Test description"},
                tags=[
                    {"name": "tag1", "display_name": "Tag 1"},
                    {"name": "tag2", "display_name": "Tag 2"},
                ],
            ),
            tag_key="test_scenario",
        )
        tags_dict = scenario.get_tags_dict()
        assert tags_dict["tag1"]["tag_name"] == "tag1"
        assert tags_dict["tag2"]["tag_name"] == "tag2"

        scenario.id = 1
        scenario.created_at = "2024-01-01"
        scenario.updated_at = "2024-01-02"
        result = scenario.to_dict()
        assert result["id"] == 1
        assert result["name"] == "test_scenario"
        assert result["display_name"] == "Test Scenario"
        assert result["description"] == "Test description"
        assert result["created_at"] == "2024-01-01"
        assert result["updated_at"] == "2024-01-02"
