"""TagGlobalPipeline / TagGlobalDataLoader 单元测试。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

from core.modules.tag.core.data_class import Scenario
from core.modules.tag.core.engines.global_based import (
    GLOBAL_ENTITY_ID,
    TagGlobalDataLoader,
    TagGlobalPipeline,
)
from core.modules.tag.core.engines.shared.hooks import TagHooks
from core.modules.tag.core.engines.shared.hooks.hook_params import TagContext
from core.modules.tag.core.engines.shared.tag_settings import TagSettings
from core.modules.tag.core.enums import TagUpdateMode
from core.modules.tag.core.services.discovery.data.discovered_tag import DiscoveredTagInfo


class _MacroHooks(TagHooks):
    def calculate_tag(self, ctx: TagContext) -> Optional[Dict[str, Any]]:
        rows = ctx.data.items.get("macro.gdp") or []
        if not rows:
            return None
        return {"value": {"n": len(rows), "as_of": ctx.data.now}}


def _settings(*, update_mode: str = "refresh") -> dict:
    return {
        "is_enabled": True,
        "meta": {"key": "macro_demo", "display_name": "macro"},
        "calculation": {
            "update_mode": update_mode,
            "recompute": update_mode == "refresh",
            "execution": {
                "mode": "entity_based",
                "start_date": "20240102",
                "end_date": "20240105",
            },
        },
        "data": {
            "base": {"data_key": "macro.gdp", "params": {}},
            "required": [],
            "min_required_records": 0,
        },
        "tag_definitions": [{"name": "gdp_tag", "display_name": "GDP"}],
    }


def _scenario(*, update_mode: str = "refresh") -> Scenario:
    ts = TagSettings.from_dict(
        _settings(update_mode=update_mode), tag_key="demo/macro"
    )
    ts.apply_defaults()
    scenario = Scenario.from_tag_settings(ts)
    scenario.tag_definitions[0].id = 7
    return scenario


def _tag_info() -> DiscoveredTagInfo:
    return DiscoveredTagInfo(
        unique_relative_path="demo/macro",
        tag_file=Path("/tmp/demo/macro/tag.py"),
        settings_file=Path("/tmp/demo/macro/settings.py"),
        folder=Path("/tmp/demo/macro"),
        key="macro_demo",
        display_name="macro",
        is_enabled=True,
        settings=_settings(),
        hooks_class=_MacroHooks,
        hooks_module_path="_ntq_tag_tag_demo_macro",
        hooks_class_name="_MacroHooks",
        hooks_file_path=Path("/tmp/demo/macro/tag.py"),
    )


class TestTagGlobalDataLoader:
    def test_slice_items_uses_global_key(self):
        contract = MagicMock()
        contract.until.return_value = {"_global": [{"quarter": "2024Q1"}]}
        items = TagGlobalDataLoader.slice_items(
            {"macro.gdp": contract}, "20240315"
        )
        assert items["macro.gdp"] == [{"quarter": "2024Q1"}]
        contract.until.assert_called_once_with("20240315")


class TestTagGlobalPipeline:
    @patch(
        "core.modules.tag.core.engines.global_based.pipeline.TagPriorValues.fetch_batch",
        return_value={},
    )
    @patch(
        "core.modules.tag.core.engines.global_based.pipeline.TagGlobalDataLoader.load"
    )
    @patch(
        "core.modules.tag.core.engines.global_based.pipeline.TagGlobalDataLoader.slice_items"
    )
    @patch(
        "core.modules.tag.core.engines.global_based.pipeline.Timeline.from_calendar_window"
    )
    @patch(
        "core.modules.tag.core.engines.global_based.pipeline.TagHookRuntime.from_tag_info"
    )
    def test_runs_calculate_tag_and_buffers(
        self,
        mock_runtime_factory,
        mock_timeline,
        mock_slice,
        mock_load,
        _mock_priors,
    ):
        runtime = MagicMock()
        runtime.call.side_effect = lambda method, ctx: {
            "value": {"as_of": ctx.data.now, "n": 1}
        }
        mock_runtime_factory.return_value = (runtime, None)

        mock_timeline.return_value = MagicMock(
            points=["20240102", "20240103", "20240104"]
        )
        mock_load.return_value = {"macro.gdp": MagicMock()}
        mock_slice.side_effect = lambda contracts, as_of: {
            "macro.gdp": [{"quarter": "2023Q4", "as_of": as_of}]
        }

        tags = MagicMock()
        result = TagGlobalPipeline.run(
            tag_info=_tag_info(),
            scenario=_scenario(update_mode="refresh"),
            entity_ids=[GLOBAL_ENTITY_ID],
            tag_data_service=tags,
            dry_run=True,
        )
        assert result["success"] is True
        assert result["tag_values_count"] == 3
        assert runtime.call.call_count == 3
        tags.mark_entity_calc_progress.assert_not_called()

    @patch(
        "core.modules.tag.core.engines.global_based.pipeline.TagPriorValues.fetch_batch",
        return_value={},
    )
    @patch(
        "core.modules.tag.core.engines.global_based.pipeline.TagGlobalDataLoader.load"
    )
    @patch(
        "core.modules.tag.core.engines.global_based.pipeline.TagGlobalDataLoader.slice_items"
    )
    @patch(
        "core.modules.tag.core.engines.global_based.pipeline.Timeline.from_calendar_window"
    )
    @patch(
        "core.modules.tag.core.engines.global_based.pipeline.TagHookRuntime.from_tag_info"
    )
    def test_incremental_marks_progress(
        self,
        mock_runtime_factory,
        mock_timeline,
        mock_slice,
        mock_load,
        _mock_priors,
    ):
        runtime = MagicMock()
        runtime.call.return_value = {"value": 1}
        mock_runtime_factory.return_value = (runtime, None)
        mock_timeline.return_value = MagicMock(points=["20240102"])
        mock_load.return_value = {"macro.gdp": MagicMock()}
        mock_slice.return_value = {"macro.gdp": [{"x": 1}]}

        scenario = _scenario(update_mode="incremental")
        assert scenario.effective_update_mode() == TagUpdateMode.INCREMENTAL.value

        tags = MagicMock()
        tags.get_entity_calc_progress.return_value = {}
        result = TagGlobalPipeline.run(
            tag_info=_tag_info(),
            scenario=scenario,
            entity_ids=[GLOBAL_ENTITY_ID],
            tag_data_service=tags,
            dry_run=False,
        )
        assert result["success"] is True
        tags.mark_entity_calc_progress.assert_called_once()
        args = tags.mark_entity_calc_progress.call_args[0]
        assert args[0] == scenario.name
        assert GLOBAL_ENTITY_ID in args[1]
