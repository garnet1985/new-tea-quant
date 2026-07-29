"""TagNonTimeSeriesPipeline / TagNonTimeSeriesDataLoader 单元测试。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

from core.modules.tag.core.data_class import Scenario
from core.modules.tag.core.engines.global_based import GLOBAL_ENTITY_ID
from core.modules.tag.core.engines.non_time_series import (
    TagNonTimeSeriesDataLoader,
    TagNonTimeSeriesPipeline,
)
from core.modules.tag.core.engines.per_entity.shared.hooks import TagHooks
from core.modules.tag.core.engines.per_entity.shared.hooks.hook_params import TagContext
from core.modules.tag.core.engines.per_entity.shared.tag_settings import TagSettings
from core.modules.tag.core.enums import TagUpdateMode
from core.modules.tag.core.services.discovery.data.discovered_tag import EnabledTagInfo


class _ListHooks(TagHooks):
    def calculate_tag(self, ctx: TagContext) -> Optional[Dict[str, Any]]:
        rows = ctx.data.items.get("stock.list") or []
        if not rows:
            return None
        return {"value": {"n": len(rows), "as_of": ctx.data.now}}


def _settings(*, update_mode: str = "refresh") -> dict:
    return {
        "is_enabled": True,
        "meta": {"key": "list_demo", "display_name": "list"},
        "calculation": {
            "update_mode": update_mode,
            "recompute": update_mode == "refresh",
            "execution": {
                "start_date": "20240102",
                "end_date": "20240105",
            },
        },
        "data": {
            "base": {"data_key": "stock.list", "params": {}},
            "required": [],
            "min_required_records": 0,
        },
        "tag_definitions": [{"name": "list_size", "display_name": "List size"}],
    }


def _scenario(*, update_mode: str = "refresh") -> Scenario:
    ts = TagSettings.from_dict(
        _settings(update_mode=update_mode), tag_key="demo/list"
    )
    ts.apply_defaults()
    scenario = Scenario.from_tag_settings(ts)
    scenario.tag_definitions[0].id = 9
    return scenario


def _tag_info() -> EnabledTagInfo:
    return EnabledTagInfo(
        unique_relative_path="demo/list",
        tag_file=Path("/tmp/demo/list/tag.py"),
        settings_file=Path("/tmp/demo/list/settings.py"),
        folder=Path("/tmp/demo/list"),
        key="list_demo",
        display_name="list",
        is_enabled=True,
        settings=_settings(),
        hooks_class=_ListHooks,
        hooks_module_path="_ntq_tag_tag_demo_list",
        hooks_class_name="_ListHooks",
        hooks_file_path=Path("/tmp/demo/list/tag.py"),
    )


class TestTagNonTimeSeriesDataLoader:
    def test_to_items_from_get_data(self):
        contract = MagicMock()
        contract.get_data.return_value = [{"id": "600000.SH"}, {"id": "000001.SZ"}]
        with patch(
            "core.modules.tag.core.engines.non_time_series.data_loader.DataSettings.is_time_series",
            return_value=False,
        ):
            items = TagNonTimeSeriesDataLoader.to_items(
                {"stock.list": contract}, as_of="20240105"
            )
        assert len(items["stock.list"]) == 2
        contract.get_data.assert_called_once()
        contract.until.assert_not_called()


class TestTagNonTimeSeriesPipeline:
    @patch(
        "core.modules.tag.core.engines.non_time_series.pipeline.TagPriorValues.fetch_batch",
        return_value={},
    )
    @patch(
        "core.modules.tag.core.engines.non_time_series.pipeline.TagNonTimeSeriesDataLoader.load"
    )
    @patch(
        "core.modules.tag.core.engines.non_time_series.pipeline.TagNonTimeSeriesDataLoader.to_items"
    )
    @patch(
        "core.modules.tag.core.engines.non_time_series.pipeline.TagHookRuntime.from_tag_info"
    )
    def test_runs_calculate_tag_once(
        self,
        mock_runtime_factory,
        mock_items,
        mock_load,
        _mock_priors,
    ):
        runtime = MagicMock()
        runtime.call.side_effect = lambda method, ctx: {
            "value": {"n": len(ctx.data.items.get("stock.list") or []), "as_of": ctx.data.now}
        }
        mock_runtime_factory.return_value = (runtime, None)
        mock_load.return_value = {"stock.list": MagicMock()}
        mock_items.return_value = {
            "stock.list": [{"id": "a"}, {"id": "b"}, {"id": "c"}]
        }

        tags = MagicMock()
        result = TagNonTimeSeriesPipeline.run(
            tag_info=_tag_info(),
            scenario=_scenario(update_mode="refresh"),
            entity_ids=[GLOBAL_ENTITY_ID],
            tag_data_service=tags,
            dry_run=True,
        )
        assert result["success"] is True
        assert result["tag_values_count"] == 1
        assert result["as_of"] == "20240105"
        assert runtime.call.call_count == 1
        tags.mark_entity_calc_progress.assert_not_called()

    @patch(
        "core.modules.tag.core.engines.non_time_series.pipeline.TagPriorValues.fetch_batch",
        return_value={},
    )
    @patch(
        "core.modules.tag.core.engines.non_time_series.pipeline.TagNonTimeSeriesDataLoader.load"
    )
    @patch(
        "core.modules.tag.core.engines.non_time_series.pipeline.TagNonTimeSeriesDataLoader.to_items"
    )
    @patch(
        "core.modules.tag.core.engines.non_time_series.pipeline.TagHookRuntime.from_tag_info"
    )
    def test_incremental_marks_progress(
        self,
        mock_runtime_factory,
        mock_items,
        mock_load,
        _mock_priors,
    ):
        runtime = MagicMock()
        runtime.call.return_value = {"value": 1}
        mock_runtime_factory.return_value = (runtime, None)
        mock_load.return_value = {"stock.list": MagicMock()}
        mock_items.return_value = {"stock.list": [{"id": "a"}]}

        scenario = _scenario(update_mode="incremental")
        assert scenario.effective_update_mode() == TagUpdateMode.INCREMENTAL.value

        tags = MagicMock()
        tags.get_entity_calc_progress.return_value = {}
        result = TagNonTimeSeriesPipeline.run(
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
