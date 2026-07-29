"""TagCalcWindowResolver 单元测试（progress 来自 TagDataService / DB）。"""

from __future__ import annotations

from unittest.mock import MagicMock

from core.modules.tag.core.data_class.scenario import Scenario
from core.modules.tag.core.engines.per_entity.shared.calc_window import TagCalcWindowResolver
from core.modules.tag.core.engines.per_entity.shared.tag_settings import TagSettings
from core.modules.tag.core.enums import TagUpdateMode


def _settings() -> TagSettings:
    raw = {
        "is_enabled": True,
        "meta": {"key": "cap"},
        "calculation": {
            "update_mode": "incremental",
            "execution": {
                "mode": "entity_based",
                "start_date": "20230101",
                "end_date": "20230110",
            },
        },
        "data": {
            "base": {"data_key": "stock.kline.daily", "params": {}},
            "required": [],
            "min_required_records": 0,
        },
        "tag_definitions": [{"name": "t1"}],
    }
    ts = TagSettings.from_dict(raw, tag_key="demo/cap")
    ts.apply_defaults()
    return ts


def _scenario(*, update_mode: str = "incremental") -> Scenario:
    return Scenario(
        name="demo/cap",
        key="cap",
        update_mode=update_mode,
        start_date="20230101",
        end_date="20230110",
    )


def _tags_with_progress(progress: dict) -> MagicMock:
    tags = MagicMock()
    tags.get_entity_calc_progress.return_value = dict(progress)
    return tags


class TestTagCalcWindowResolver:
    def test_refresh_uses_full_window(self):
        windows = TagCalcWindowResolver.resolve(
            scenario=_scenario(update_mode="refresh"),
            settings=_settings(),
            entity_ids=["a", "b"],
            tag_data_service=_tags_with_progress({}),
        )
        assert windows.data_start == "20230101"
        assert windows.data_end == "20230110"
        assert [e.entity_id for e in windows.entities] == ["a", "b"]
        assert windows.entities[0].start_date == "20230101"

    def test_incremental_advances_from_last_calculated_end(self):
        tags = _tags_with_progress({"a": "20230105", "b": "20230101"})
        windows = TagCalcWindowResolver.resolve(
            scenario=_scenario(update_mode=TagUpdateMode.INCREMENTAL.value),
            settings=_settings(),
            entity_ids=["a", "b"],
            tag_data_service=tags,
        )
        by_id = {e.entity_id: e for e in windows.entities}
        assert by_id["a"].start_date == "20230106"
        assert by_id["b"].start_date == "20230102"
        assert windows.data_start == "20230102"
        assert windows.data_end == "20230110"
        assert windows.skipped_up_to_date == 0
        tags.get_entity_calc_progress.assert_called_once_with("demo/cap")

    def test_incremental_ignores_max_as_of_from_db(self):
        """as_of 水位不得影响窗口（变化日写入场景）。"""
        tags = _tags_with_progress({})
        tags.get_tag_value_last_update_info.return_value = {
            "a": {"max_as_of_date": "20230105"},
        }
        windows = TagCalcWindowResolver.resolve(
            scenario=_scenario(),
            settings=_settings(),
            entity_ids=["a"],
            tag_data_service=tags,
        )
        assert windows.entities[0].start_date == "20230101"
        tags.get_tag_value_last_update_info.assert_not_called()
        tags.get_entity_calc_progress.assert_called_once()

    def test_incremental_skips_up_to_date_entities(self):
        tags = _tags_with_progress({"a": "20230110", "b": "20230109"})
        windows = TagCalcWindowResolver.resolve(
            scenario=_scenario(),
            settings=_settings(),
            entity_ids=["a", "b"],
            tag_data_service=tags,
        )
        assert [e.entity_id for e in windows.entities] == ["b"]
        assert windows.entities[0].start_date == "20230110"
        assert windows.skipped_up_to_date == 1

    def test_incremental_all_caught_up_returns_empty(self):
        tags = _tags_with_progress({"a": "20230110"})
        windows = TagCalcWindowResolver.resolve(
            scenario=_scenario(),
            settings=_settings(),
            entity_ids=["a"],
            tag_data_service=tags,
        )
        assert windows.entities == []
        assert windows.skipped_up_to_date == 1

    def test_incremental_without_service_starts_from_default(self):
        windows = TagCalcWindowResolver.resolve(
            scenario=_scenario(),
            settings=_settings(),
            entity_ids=["a"],
            tag_data_service=None,
        )
        assert windows.entities[0].start_date == "20230101"
