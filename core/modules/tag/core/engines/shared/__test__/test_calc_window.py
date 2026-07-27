"""TagCalcWindowResolver / TagCalcProgressStore 单元测试。"""

from __future__ import annotations

from unittest.mock import MagicMock

from core.modules.tag.core.data_class.scenario import Scenario
from core.modules.tag.core.engines.shared.calc_progress import TagCalcProgressStore
from core.modules.tag.core.engines.shared.calc_window import TagCalcWindowResolver
from core.modules.tag.core.engines.shared.tag_settings import TagSettings
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


class TestTagCalcWindowResolver:
    def test_refresh_uses_full_window(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            TagCalcProgressStore,
            "_root",
            classmethod(lambda cls: tmp_path),
        )
        windows = TagCalcWindowResolver.resolve(
            scenario=_scenario(update_mode="refresh"),
            settings=_settings(),
            entity_ids=["a", "b"],
            tag_data_service=MagicMock(),
        )
        assert windows.data_start == "20230101"
        assert windows.data_end == "20230110"
        assert [e.entity_id for e in windows.entities] == ["a", "b"]
        assert windows.entities[0].start_date == "20230101"

    def test_incremental_advances_from_last_calculated_end(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(
            TagCalcProgressStore,
            "_root",
            classmethod(lambda cls: tmp_path),
        )
        TagCalcProgressStore.mark_entities(
            "demo/cap",
            {"a": "20230105", "b": "20230101"},
        )
        windows = TagCalcWindowResolver.resolve(
            scenario=_scenario(update_mode=TagUpdateMode.INCREMENTAL.value),
            settings=_settings(),
            entity_ids=["a", "b"],
            tag_data_service=MagicMock(),
        )
        by_id = {e.entity_id: e for e in windows.entities}
        assert by_id["a"].start_date == "20230106"
        assert by_id["b"].start_date == "20230102"
        assert windows.data_start == "20230102"
        assert windows.data_end == "20230110"
        assert windows.skipped_up_to_date == 0

    def test_incremental_ignores_max_as_of_from_db(self, tmp_path, monkeypatch):
        """as_of 水位不得影响窗口（变化日写入场景）。"""
        monkeypatch.setattr(
            TagCalcProgressStore,
            "_root",
            classmethod(lambda cls: tmp_path),
        )
        tags = MagicMock()
        tags.get_tag_value_last_update_info.return_value = {
            "a": {"max_as_of_date": "20230105"},
        }
        # 无 progress → 应从 default_start 起，而不是 as_of+1
        windows = TagCalcWindowResolver.resolve(
            scenario=_scenario(),
            settings=_settings(),
            entity_ids=["a"],
            tag_data_service=tags,
        )
        assert windows.entities[0].start_date == "20230101"
        tags.get_tag_value_last_update_info.assert_not_called()

    def test_incremental_skips_up_to_date_entities(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            TagCalcProgressStore,
            "_root",
            classmethod(lambda cls: tmp_path),
        )
        TagCalcProgressStore.mark_entities(
            "demo/cap",
            {"a": "20230110", "b": "20230109"},
        )
        windows = TagCalcWindowResolver.resolve(
            scenario=_scenario(),
            settings=_settings(),
            entity_ids=["a", "b"],
            tag_data_service=MagicMock(),
        )
        assert [e.entity_id for e in windows.entities] == ["b"]
        assert windows.entities[0].start_date == "20230110"
        assert windows.skipped_up_to_date == 1

    def test_incremental_all_caught_up_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            TagCalcProgressStore,
            "_root",
            classmethod(lambda cls: tmp_path),
        )
        TagCalcProgressStore.mark_entities("demo/cap", {"a": "20230110"})
        windows = TagCalcWindowResolver.resolve(
            scenario=_scenario(),
            settings=_settings(),
            entity_ids=["a"],
            tag_data_service=MagicMock(),
        )
        assert windows.entities == []
        assert windows.skipped_up_to_date == 1
