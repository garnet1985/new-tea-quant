"""ScenarioModel 单元测试。"""
from __future__ import annotations

import pytest

from core.modules.tag.enums import TagUpdateMode
from core.modules.tag.models.scenario_model import ScenarioModel

_STOCK_KLINE = {"data_id": "stock.kline.daily", "params": {"adjust": "qfq"}}


def _stock_scenario(**overrides) -> dict:
    base = {
        "name": "test_scenario",
        "target_entity": {"type": "stock_kline_daily"},
        "is_enabled": True,
        "data": {"required": [_STOCK_KLINE]},
        "tags": [{"name": "tag1"}],
        "incremental_required_records_before_as_of_date": 10,
    }
    base.update(overrides)
    return base


class TestScenarioModel:
    def test_create_from_settings(self):
        scenario = ScenarioModel.create_from_settings(
            _stock_scenario(
                display_name="Test Scenario Display",
                description="Test description",
                tags=[
                    {"name": "tag1", "display_name": "Tag 1"},
                    {"name": "tag2", "display_name": "Tag 2"},
                ],
            )
        )
        assert scenario.name == "test_scenario"
        assert scenario.get_target_entity() == "stock_kline_daily"
        assert scenario.is_enabled() is True
        assert scenario.display_name == "Test Scenario Display"
        assert scenario.description == "Test description"
        assert [t.get_name() for t in scenario.get_tag_models()] == ["tag1", "tag2"]

        default = ScenarioModel.create_from_settings(_stock_scenario())
        assert default.display_name == "test_scenario"

    def test_create_from_settings_rejects_string_target_entity(self):
        assert ScenarioModel.create_from_settings(
            _stock_scenario(target_entity="stock_kline_daily")
        ) is None

    @pytest.mark.parametrize(
        "settings,expected",
        [
            (_stock_scenario(), True),
            (
                {
                    "name": "macro_general",
                    "tag_target_type": "general",
                    "is_enabled": True,
                    "data": {
                        "required": [{"data_id": "macro.gdp", "params": {}}],
                        "tag_time_axis_based_on": "macro.gdp",
                    },
                    "tags": [{"name": "macro_tag"}],
                    "incremental_required_records_before_as_of_date": 0,
                },
                True,
            ),
            (
                {
                    "name": "test_scenario",
                    "target_entity": {"type": "stock_kline_daily"},
                    "is_enabled": True,
                },
                False,
            ),
            (
                {
                    "name": "test_scenario",
                    "is_enabled": True,
                    "data": {"required": [_STOCK_KLINE]},
                    "tags": [{"name": "tag1"}],
                },
                False,
            ),
            (_stock_scenario(tags=[]), False),
            (
                _stock_scenario(
                    update_mode="incremental",
                    incremental_required_records_before_as_of_date=-1,
                ),
                False,
            ),
            (
                {
                    "name": "test_scenario",
                    "target_entity": {"type": "stock_kline_daily"},
                    "is_enabled": True,
                    "data": {"required": [_STOCK_KLINE]},
                    "tags": [{"name": "tag1"}],
                    "update_mode": "incremental",
                },
                False,
            ),
            (
                {
                    "name": "macro_general",
                    "tag_target_type": "general",
                    "is_enabled": True,
                    "data": {"required": [{"data_id": "macro.gdp", "params": {}}]},
                    "tags": [{"name": "macro_tag"}],
                    "incremental_required_records_before_as_of_date": 0,
                },
                False,
            ),
        ],
    )
    def test_is_setting_valid(self, settings, expected):
        assert ScenarioModel.is_setting_valid(settings) is expected

    @pytest.mark.parametrize(
        "overrides,expected",
        [
            ({"update_mode": "incremental"}, TagUpdateMode.INCREMENTAL),
            ({"update_mode": "refresh"}, TagUpdateMode.REFRESH),
            ({}, TagUpdateMode.INCREMENTAL),
        ],
    )
    def test_calculate_update_mode(self, overrides, expected):
        scenario = ScenarioModel.create_from_settings(_stock_scenario(**overrides))
        assert scenario.calculate_update_mode() == expected

    def test_recompute_forces_refresh(self):
        scenario = ScenarioModel.create_from_settings(_stock_scenario(recompute=True))
        assert scenario.should_recompute() is True
        assert scenario.calculate_update_mode() == TagUpdateMode.REFRESH

    def test_get_tags_dict_and_to_dict(self):
        scenario = ScenarioModel.create_from_settings(
            _stock_scenario(
                display_name="Test Scenario",
                description="Test description",
                tags=[
                    {"name": "tag1", "display_name": "Tag 1"},
                    {"name": "tag2", "display_name": "Tag 2"},
                ],
            )
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
