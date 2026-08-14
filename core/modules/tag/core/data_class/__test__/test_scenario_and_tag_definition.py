"""Scenario / TagDefinition 单元测试。"""

from __future__ import annotations

from core.modules.tag.core.data_class import Scenario, TagDefinition
from core.modules.tag.core.engines.shared.tag_settings import TagSettings


def _userspace_settings(**overrides) -> dict:
    base = {
        "is_enabled": True,
        "meta": {"key": "cap_tier", "display_name": "市值档", "description": "desc"},
        "calculation": {
            "update_mode": "incremental",
            "recompute": False,
            "execution": {"mode": "entity_based", "start_date": "20240101", "end_date": ""},
        },
        "data": {
            "base": {"data_key": "stock.kline.daily", "params": {"adjust": "qfq"}},
            "required": [],
            "min_required_records": 0,
        },
        "tag_definitions": [
            {"name": "market_cap_tier", "display_name": "市值", "description": "tier"},
        ],
    }
    for key, value in overrides.items():
        if key in ("calculation", "data", "meta") and isinstance(value, dict):
            nested = dict(base.get(key) or {})
            nested.update(value)
            base[key] = nested
        else:
            base[key] = value
    return base


class TestTagDefinition:
    def test_from_settings_item_and_roundtrip(self):
        d = TagDefinition.from_settings_item(
            {"name": "t1", "display_name": "T1", "description": "d"}
        )
        assert d.name == "t1"
        assert d.id is None
        assert d.is_persisted is False
        payload = d.to_dict()
        assert payload["name"] == "t1"
        restored = TagDefinition.from_dict({**payload, "id": 7, "scenario_id": 3})
        assert restored.id == 7
        assert restored.scenario_id == 3
        assert restored.is_persisted is True

    def test_apply_db_meta_and_diff(self):
        d = TagDefinition.from_settings_item({"name": "t1", "display_name": "A"})
        d.apply_db_meta(
            {
                "id": 1,
                "scenario_id": 2,
                "display_name": "A",
                "description": "",
                "created_at": "x",
                "updated_at": "y",
            }
        )
        assert d.id == 1
        assert d.has_meta_diff({"display_name": "A", "description": ""}) is False
        assert d.has_meta_diff({"display_name": "B", "description": ""}) is True


class TestScenario:
    def test_from_tag_settings(self):
        ts = TagSettings.from_dict(
            _userspace_settings(), tag_key="demo/market_cap_tier"
        )
        assert ts.validate().is_usable()
        scenario = Scenario.from_tag_settings(ts)
        assert scenario.name == "demo/market_cap_tier"
        assert scenario.key == "cap_tier"
        assert scenario.display_name == "市值档"
        assert scenario.attach_to_data_key == "stock.kline.daily"
        assert scenario.target_entity_type == "stock_kline_daily"
        assert scenario.is_entity_based is True
        assert scenario.effective_update_mode() == "incremental"
        assert scenario.is_dry_run is False
        assert [d.name for d in scenario.tag_definitions] == ["market_cap_tier"]
        assert scenario.definitions_by_name()["market_cap_tier"].display_name == "市值"
        assert scenario.settings["execution_mode"] == "entity_based"

    def test_is_dry_run_from_settings(self):
        ts = TagSettings.from_dict(
            _userspace_settings(
                calculation={
                    "update_mode": "incremental",
                    "is_dry_run": True,
                    "execution": {"mode": "entity_based"},
                }
            ),
            tag_key="demo/x",
        )
        scenario = Scenario.from_tag_settings(ts)
        assert scenario.is_dry_run is True

    def test_recompute_forces_refresh(self):
        ts = TagSettings.from_dict(
            _userspace_settings(
                calculation={
                    "update_mode": "incremental",
                    "recompute": True,
                    "execution": {"mode": "entity_based"},
                }
            ),
            tag_key="demo/x",
        )
        scenario = Scenario.from_tag_settings(ts)
        assert scenario.recompute is True
        assert scenario.effective_update_mode() == "refresh"

    def test_job_dict_and_from_dict_roundtrip(self):
        ts = TagSettings.from_dict(
            _userspace_settings(), tag_key="demo/market_cap_tier"
        )
        scenario = Scenario.from_tag_settings(ts)
        scenario.apply_db_meta({"id": 9, "display_name": "市值档", "description": "desc"})
        scenario.tag_definitions[0].apply_db_meta(
            {"id": 11, "scenario_id": 9, "display_name": "市值", "description": "tier"}
        )
        job = scenario.to_job_dict()
        assert job["id"] == 9
        assert job["tag_definitions"][0]["id"] == 11
        restored = Scenario.from_dict(job)
        assert restored.id == 9
        assert restored.tag_definitions[0].id == 11
        assert restored.key == "cap_tier"
