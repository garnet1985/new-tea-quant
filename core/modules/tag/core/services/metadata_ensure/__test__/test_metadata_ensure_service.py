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
) -> Scenario:
    return Scenario(
        name="demo/cap",
        key="cap",
        display_name=display_name,
        description="d",
        recompute=recompute,
        update_mode=update_mode,
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
        tags.save_scenario.assert_called_once()
        tags.save.assert_called_once_with("tier", 10, "Tier", "t")

    def test_refresh_clears_values_without_recreate(self):
        tags = MagicMock()
        tags.load_scenario.return_value = {
            "id": 10,
            "display_name": "Demo",
            "description": "d",
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
        tags.delete_scenario.assert_not_called()
        tags.save_scenario.assert_not_called()
        assert scenario.id == 10
        assert scenario.tag_definitions[0].id == 20

    def test_recompute_recreates_scenario_and_tags(self):
        tags = MagicMock()
        tags.load_scenario.side_effect = [
            {"id": 10, "display_name": "Demo", "description": "d"},
        ]
        tags.save_scenario.return_value = {
            "id": 11,
            "display_name": "Demo",
            "description": "d",
        }
        tags.load.return_value = None
        tags.save.return_value = {
            "id": 21,
            "scenario_id": 11,
            "display_name": "Tier",
            "description": "t",
        }

        scenario = _scenario(recompute=True)
        MetadataEnsureService(tags).ensure(scenario)

        tags.delete_tag_values_by_scenario.assert_called_once_with(10)
        tags.delete_tag_definitions_by_scenario.assert_called_once_with(10)
        tags.delete_scenario.assert_called_once_with(10, cascade=False)
        assert scenario.id == 11
        assert scenario.tag_definitions[0].id == 21

    def test_updates_when_display_name_differs(self):
        tags = MagicMock()
        tags.load_scenario.return_value = {
            "id": 10,
            "display_name": "Old",
            "description": "d",
        }
        tags.update_scenario.return_value = {
            "id": 10,
            "display_name": "Demo",
            "description": "d",
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
