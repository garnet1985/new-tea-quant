"""MetadataEnsureService 单元测试（mock TagDataService）。"""

from __future__ import annotations

from unittest.mock import MagicMock

from core.modules.tag.core.data_class import Scenario, TagDefinition
from core.modules.tag.core.services.metadata_ensure import MetadataEnsureService


def _scenario(
    *,
    recompute: bool = False,
    update_mode: str = "incremental",
    display_name: str = "Demo",
    key: str = "cap",
    attach_to_data_key: str = "stock.kline.daily",
    is_dry_run: bool = False,
) -> Scenario:
    return Scenario(
        name="demo/cap",
        key=key,
        display_name=display_name,
        description="d",
        recompute=recompute,
        update_mode=update_mode,
        attach_to_data_key=attach_to_data_key,
        is_dry_run=is_dry_run,
        tag_definitions=[
            TagDefinition(
                name="tier",
                display_name="Tier",
                description="t",
            )
        ],
    )


class TestMetadataEnsureService:
    def test_creates_scenario_and_definitions_when_missing(self):
        tags = MagicMock()
        tags.load_scenario.return_value = None
        tags.save_scenario.return_value = {
            "id": 10,
            "name": "demo/cap",
            "display_name": "Demo",
            "description": "d",
            "key": "cap",
            "attach_to_data_key": "stock.kline.daily",
            "created_at": "c",
            "updated_at": "u",
        }
        tags.load.return_value = None
        tags.save.return_value = {
            "id": 20,
            "name": "tier",
            "scenario_id": 10,
            "display_name": "Tier",
            "description": "t",
        }

        scenario = _scenario()
        MetadataEnsureService(tags).ensure(scenario)

        assert scenario.id == 10
        assert scenario.tag_definitions[0].id == 20
        assert scenario.tag_definitions[0].scenario_id == 10
        tags.save_scenario.assert_called_once_with(
            "demo/cap",
            display_name="Demo",
            description="d",
            key="cap",
            attach_to_data_key="stock.kline.daily",
        )
        tags.save.assert_called_once_with("tier", 10, "Tier", "t")

    def test_refresh_clears_values_without_recreate(self):
        tags = MagicMock()
        tags.load_scenario.return_value = {
            "id": 10,
            "display_name": "Demo",
            "description": "d",
            "key": "cap",
            "attach_to_data_key": "stock.kline.daily",
        }
        tags.load.return_value = {
            "id": 20,
            "scenario_id": 10,
            "display_name": "Tier",
            "description": "t",
        }

        scenario = _scenario(update_mode="refresh")
        MetadataEnsureService(tags).ensure(scenario)

        tags.delete_tag_values_by_scenario.assert_called_once_with(10)
        tags.clear_calc_progress_by_scenario.assert_called_once_with(10)
        tags.delete_scenario.assert_not_called()
        tags.save_scenario.assert_not_called()
        assert scenario.id == 10
        assert scenario.tag_definitions[0].id == 20

    def test_recompute_keeps_scenario_id(self):
        tags = MagicMock()
        tags.load_scenario.return_value = {
            "id": 10,
            "display_name": "Demo",
            "description": "d",
            "key": None,
            "attach_to_data_key": None,
        }
        tags.update_scenario.return_value = {
            "id": 10,
            "display_name": "Demo",
            "description": "d",
            "key": "cap",
            "attach_to_data_key": "stock.kline.daily",
        }
        tags.load.return_value = None
        tags.save.return_value = {
            "id": 21,
            "scenario_id": 10,
            "display_name": "Tier",
            "description": "t",
        }

        scenario = _scenario(recompute=True)
        MetadataEnsureService(tags).ensure(scenario)

        tags.delete_tag_values_by_scenario.assert_called_once_with(10)
        tags.delete_tag_definitions_by_scenario.assert_called_once_with(10)
        tags.clear_calc_progress_by_scenario.assert_called_once_with(10)
        tags.delete_scenario.assert_not_called()
        tags.save_scenario.assert_not_called()
        tags.update_scenario.assert_called_once()
        assert scenario.id == 10
        assert scenario.tag_definitions[0].id == 21
        assert scenario.tag_definitions[0].scenario_id == 10

    def test_updates_when_key_missing_in_db(self):
        tags = MagicMock()
        tags.load_scenario.return_value = {
            "id": 10,
            "display_name": "Demo",
            "description": "d",
            "key": None,
            "attach_to_data_key": None,
        }
        tags.update_scenario.return_value = {
            "id": 10,
            "display_name": "Demo",
            "description": "d",
            "key": "cap",
            "attach_to_data_key": "stock.kline.daily",
        }
        tags.load.return_value = {
            "id": 20,
            "scenario_id": 10,
            "display_name": "Tier",
            "description": "t",
        }

        scenario = _scenario()
        MetadataEnsureService(tags).ensure(scenario)

        tags.update_scenario.assert_called_once()
        kwargs = tags.update_scenario.call_args.kwargs
        assert kwargs["key"] == "cap"
        assert kwargs["attach_to_data_key"] == "stock.kline.daily"
        assert scenario.id == 10

    def test_updates_when_display_name_differs(self):
        tags = MagicMock()
        tags.load_scenario.return_value = {
            "id": 10,
            "display_name": "Old",
            "description": "d",
            "key": "cap",
            "attach_to_data_key": "stock.kline.daily",
        }
        tags.update_scenario.return_value = {
            "id": 10,
            "display_name": "Demo",
            "description": "d",
            "key": "cap",
            "attach_to_data_key": "stock.kline.daily",
        }
        tags.load.return_value = {
            "id": 20,
            "scenario_id": 10,
            "display_name": "OldTier",
            "description": "t",
        }
        tags.update_tag_definition.return_value = {
            "id": 20,
            "scenario_id": 10,
            "display_name": "Tier",
            "description": "t",
        }

        scenario = _scenario(display_name="Demo")
        MetadataEnsureService(tags).ensure(scenario)

        tags.update_scenario.assert_called_once()
        tags.update_tag_definition.assert_called_once()
        assert scenario.display_name == "Demo"
        assert scenario.tag_definitions[0].display_name == "Tier"

    def test_dry_run_skips_refresh_clear(self):
        tags = MagicMock()
        tags.load_scenario.return_value = {
            "id": 10,
            "display_name": "Demo",
            "description": "d",
            "key": "cap",
            "attach_to_data_key": "stock.kline.daily",
        }
        tags.load.return_value = {
            "id": 20,
            "scenario_id": 10,
            "display_name": "Tier",
            "description": "t",
        }

        scenario = _scenario(update_mode="refresh", is_dry_run=True)
        MetadataEnsureService(tags).ensure(scenario)

        tags.delete_tag_values_by_scenario.assert_not_called()
        tags.clear_calc_progress_by_scenario.assert_not_called()
        assert scenario.id == 10
        assert scenario.tag_definitions[0].id == 20

    def test_dry_run_skips_recompute_clear(self):
        tags = MagicMock()
        tags.load_scenario.return_value = {
            "id": 10,
            "display_name": "Demo",
            "description": "d",
            "key": "cap",
            "attach_to_data_key": "stock.kline.daily",
        }
        tags.update_scenario.return_value = {
            "id": 10,
            "display_name": "Demo",
            "description": "d",
            "key": "cap",
            "attach_to_data_key": "stock.kline.daily",
        }
        tags.load.return_value = {
            "id": 20,
            "scenario_id": 10,
            "display_name": "Tier",
            "description": "t",
        }

        scenario = _scenario(recompute=True, is_dry_run=True)
        MetadataEnsureService(tags).ensure(scenario)

        tags.delete_tag_values_by_scenario.assert_not_called()
        tags.delete_tag_definitions_by_scenario.assert_not_called()
        tags.clear_calc_progress_by_scenario.assert_not_called()
        tags.delete_tag_definition.assert_not_called()
        tags.save.assert_not_called()
        assert scenario.id == 10
        assert scenario.tag_definitions[0].id == 20
