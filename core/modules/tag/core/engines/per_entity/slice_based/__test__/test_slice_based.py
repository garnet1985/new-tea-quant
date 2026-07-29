"""Tag slice_based hooks / builder / executor 单测。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

from core.modules.backtest_engine.core.shared.jobs import BacktestJob
from core.modules.backtest_engine.core.shared.types import JobContext
from core.modules.tag.core.data_class import Scenario, TagDefinition
from core.modules.tag.core.engines.shared.data_class import TagCalendarAsOfResult
from core.modules.tag.core.engines.shared.hooks import (
    TagContext,
    TagHookRuntime,
    TagHooks,
)
from core.modules.tag.core.engines.shared.tag_settings import TagSettings
from core.modules.tag.core.engines.per_entity.slice_based import (
    SliceTaskState,
    TagSliceJobBuilder,
    TagSliceJobExecutor,
)
from core.modules.tag.core.services.discovery.data.discovered_tag import DiscoveredTagInfo


class _EchoHooks(TagHooks):
    def calculate_tag(self, ctx: TagContext) -> Optional[Dict[str, Any]]:
        definition = ctx.data.tag_definition
        assert definition is not None
        return {"value": f"{ctx.data.entity_id}:{definition.name}:{ctx.data.now}"}


class _CalendarHooks(TagHooks):
    def calculate_tag(self, ctx: TagContext) -> Optional[Dict[str, Any]]:
        return None

    def on_calendar_asof(self, ctx: TagContext) -> TagCalendarAsOfResult:
        return TagCalendarAsOfResult(
            as_of_date=ctx.data.now,
            entity_tags={
                "e1": [{"tag_name": "tier", "value": "high"}],
            },
            session_state={"n": 1},
        )


def _settings_dict() -> dict:
    return {
        "is_enabled": True,
        "meta": {"key": "cap", "display_name": "cap"},
        "calculation": {
            "update_mode": "refresh",
            "recompute": True,
            "execution": {
                "mode": "slice_based",
                "start_date": "20240102",
                "end_date": "20240105",
            },
        },
        "data": {
            "base": {"data_key": "stock.kline.daily", "params": {"adjust": "qfq"}},
            "required": [],
            "min_required_records": 1,
        },
        "tag_definitions": [{"name": "tier", "display_name": "Tier"}],
    }


def _bar(date: str = "20240102") -> dict:
    return {"date": date, "open": 1, "high": 1, "low": 1, "close": 1}


def _enabled_tag_info() -> DiscoveredTagInfo:
    return DiscoveredTagInfo(
        unique_relative_path="demo/cap",
        tag_file=Path("/tmp/demo/cap/tag.py"),
        settings_file=Path("/tmp/demo/cap/settings.py"),
        folder=Path("/tmp/demo/cap"),
        key="cap",
        display_name="cap",
        is_enabled=True,
        settings=_settings_dict(),
        hooks_class=_EchoHooks,
        hooks_module_path="_ntq_tag_tag_demo_cap",
        hooks_class_name="_EchoHooks",
        hooks_file_path=Path("/tmp/demo/cap/tag.py"),
    )


class TestTagContext:
    def test_assemble_and_fill(self):
        ts = TagSettings.from_dict(_settings_dict(), tag_key="demo/cap")
        ts.apply_defaults()
        base = TagContext.assemble(
            tag_key="cap",
            settings=ts,
            entity_list=["e1", "e2"],
            tag_path="demo/cap",
        )
        definition = TagDefinition.from_settings_item({"name": "tier"})
        filled = TagContext.fill(
            base,
            now="20240102",
            items={"stock.kline.daily": [_bar()]},
            entity_id="e1",
            tag_definition=definition,
        )
        assert filled.data.now == "20240102"
        assert filled.data.entity_id == "e1"
        assert filled.data.tag_definition is not None
        assert filled.data.tag_definition.name == "tier"
        filled.custom["x"] = 1
        assert base.custom["x"] == 1


class TestTagSliceJobBuilder:
    def test_payload_shape(self):
        ts = TagSettings.from_dict(_settings_dict(), tag_key="demo/cap")
        assert ts.validate().is_usable(), ts.validate().errors
        scenario = Scenario.from_tag_settings(ts)
        scenario.tag_definitions[0].id = 7

        with patch.object(TagSliceJobBuilder, "_count_open_dates", return_value=3):
            jobs = TagSliceJobBuilder.build_backtest_engine_jobs(
                _enabled_tag_info(),
                scenario,
                entity_ids=["e1", "e2"],
            )
        assert len(jobs) == 1
        payload = jobs[0]["payload"]
        assert payload[BacktestJob.SLICE_BASED_ENTITY_KEY] == ["e1", "e2"]
        assert payload[BacktestJob.TIMELINE_POINT_COUNT_KEY] == 3
        assert payload["tag_info"]["key"] == "cap"
        assert payload["tag_definitions"][0]["id"] == 7
        assert payload["scenario_name"] == "demo/cap"
        assert "stock.kline.daily" in payload["entity_shared"]
        assert payload["entity_specified"] == [
            {"id": "e1", "start_date": "20240102", "end_date": "20240105"},
            {"id": "e2", "start_date": "20240102", "end_date": "20240105"},
        ]

    def test_incremental_uses_progress_map(self):
        raw = _settings_dict()
        raw["calculation"]["update_mode"] = "incremental"
        raw["calculation"]["recompute"] = False
        info = _enabled_tag_info()
        info.settings = raw
        ts = TagSettings.from_dict(raw, tag_key="demo/cap")
        assert ts.validate().is_usable(), ts.validate().errors
        scenario = Scenario.from_tag_settings(ts)
        scenario.tag_definitions[0].id = 7

        tags = MagicMock()
        tags.get_entity_calc_progress.return_value = {
            "e1": "20240103",
            "e2": "20240105",
        }
        with patch.object(TagSliceJobBuilder, "_count_open_dates", return_value=2):
            jobs = TagSliceJobBuilder.build_backtest_engine_jobs(
                info,
                scenario,
                entity_ids=["e1", "e2"],
                tag_data_service=tags,
            )
        assert len(jobs) == 1
        payload = jobs[0]["payload"]
        assert payload["entity_specified"] == [
            {"id": "e1", "start_date": "20240104", "end_date": "20240105"},
        ]
        assert payload["start_date"] == "20240104"
        assert payload["end_date"] == "20240105"
        tags.get_entity_calc_progress.assert_called_once_with("demo/cap")


class TestTagSliceJobExecutor:
    def _make_state(self, hooks: TagHooks) -> SliceTaskState:
        ts = TagSettings.from_dict(_settings_dict(), tag_key="demo/cap")
        ts.apply_defaults()
        runtime = TagHookRuntime(hooks, tag_name="cap", settings=ts)
        definition = TagDefinition.from_dict(
            {"id": 7, "name": "tier", "display_name": "Tier", "scenario_id": 1}
        )
        contract = MagicMock()
        contract.get_entity_data.side_effect = lambda eid: [_bar()] if eid == "e1" else []
        return SliceTaskState(
            entity_ids=["e1"],
            settings=ts,
            hook_runtime=runtime,
            tag_name="cap",
            tag_path="demo/cap",
            tag_definitions=[definition],
            entity_contracts={"stock.kline.daily": contract},
            global_data={},
            payload={},
        )

    def test_per_entity_calculate_tag_buffers(self):
        state = self._make_state(_EchoHooks())
        sliced = {"e1": {"stock.kline.daily": [_bar()]}}
        TagSliceJobExecutor._tick_per_entity(
            state, as_of="20240102", sliced_by_entity=sliced
        )
        assert len(state.tag_values) == 1
        assert state.tag_values[0]["value"] == "e1:tier:20240102"
        assert state.tag_values[0]["tag_definition_id"] == 7

    def test_calendar_asof_buffers(self):
        state = self._make_state(_CalendarHooks())
        assert state._uses_calendar_asof is True
        sliced = {"e1": {"stock.kline.daily": [_bar()]}}
        TagSliceJobExecutor._tick_calendar_asof(
            state, as_of="20240102", sliced_by_entity=sliced
        )
        assert len(state.tag_values) == 1
        assert state.tag_values[0]["value"] == "high"
        assert state._session_state == {"n": 1}

    def test_entity_in_calc_window_skips_before_start(self):
        state = self._make_state(_EchoHooks())
        state._entity_window = {"e1": ("20240104", "20240105")}
        sliced = {"e1": {"stock.kline.daily": [_bar("20240102")]}}
        TagSliceJobExecutor._tick_per_entity(
            state, as_of="20240102", sliced_by_entity=sliced
        )
        assert state.tag_values == []
        TagSliceJobExecutor._tick_per_entity(
            state,
            as_of="20240104",
            sliced_by_entity={"e1": {"stock.kline.daily": [_bar("20240104")]}},
        )
        assert len(state.tag_values) == 1
