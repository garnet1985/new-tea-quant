"""TagValueFlushService / pipelines 单元测试。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

from core.modules.backtest_engine.contracts import JobReport, RunProgress
from core.modules.backtest_engine.core.shared.jobs import BacktestJob
from core.modules.tag.core.data_class import Scenario, TagDefinition
from core.modules.tag.core.engines.entity_based import (
    EntityTaskState,
    TagEntityJobBuilder,
    TagEntityJobExecutor,
)
from core.modules.tag.core.engines.shared.hooks import TagContext, TagHookRuntime, TagHooks
from core.modules.tag.core.engines.shared.services import TagValueFlushService
from core.modules.tag.core.engines.shared.tag_settings import TagSettings
from core.modules.tag.core.engines.slice_based import TagSlicePipeline
from core.modules.tag.core.engines.slice_based.job_builder import TagSliceJobBuilder
from core.modules.tag.core.services.discovery.data.discovered_tag import EnabledTagInfo


class _EchoHooks(TagHooks):
    def calculate_tag(self, ctx: TagContext) -> Optional[Dict[str, Any]]:
        definition = ctx.data.tag_definition
        assert definition is not None
        return {"value": f"{ctx.data.entity_id}:{definition.name}"}


def _settings_dict(*, mode: str = "slice_based") -> dict:
    return {
        "is_enabled": True,
        "meta": {"key": "cap", "display_name": "cap"},
        "calculation": {
            "update_mode": "refresh",
            "recompute": True,
            "execution": {
                "mode": mode,
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


def _enabled_tag_info(mode: str = "slice_based") -> EnabledTagInfo:
    return EnabledTagInfo(
        unique_relative_path="demo/cap",
        tag_file=Path("/tmp/demo/cap/tag.py"),
        settings_file=Path("/tmp/demo/cap/settings.py"),
        folder=Path("/tmp/demo/cap"),
        key="cap",
        display_name="cap",
        is_enabled=True,
        settings=_settings_dict(mode=mode),
        hooks_class=_EchoHooks,
        hooks_module_path="_ntq_tag_tag_demo_cap",
        hooks_class_name="_EchoHooks",
        hooks_file_path=Path("/tmp/demo/cap/tag.py"),
    )


class TestTagValueFlushService:
    def test_to_db_row_encodes_json_value(self):
        row = TagValueFlushService.to_db_row(
            {
                "entity_id": "e1",
                "entity_type": "stock",
                "attach_to_data_key": "stock.kline.daily",
                "as_of_date": "20240102",
                "tag_definition_id": 7,
                "tag_name": "tier",
                "value": "high",
            }
        )
        assert row["entity_id"] == "e1"
        assert row["tag_definition_id"] == 7
        assert "json_value" in row
        assert "high" in row["json_value"]
        assert "tag_name" not in row
        assert "entity_type" not in row
        assert "attach_to_data_key" not in row

    def test_extend_and_flush_calls_save_batch(self):
        tags = MagicMock()
        tags.save_batch.side_effect = lambda rows: len(rows)
        flush = TagValueFlushService(tags, batch_size=2)
        n = flush.extend(
            [
                {
                    "entity_id": "e1",
                    "as_of_date": "20240102",
                    "tag_definition_id": 1,
                    "value": "a",
                },
                {
                    "entity_id": "e2",
                    "as_of_date": "20240102",
                    "tag_definition_id": 1,
                    "value": "b",
                },
            ]
        )
        assert n == 2
        assert tags.save_batch.called
        assert flush.flush() >= 2

    def test_dry_run_skips_db(self):
        flush = TagValueFlushService(None, dry_run=True, batch_size=1)
        flush.extend(
            [
                {
                    "entity_id": "e1",
                    "as_of_date": "20240102",
                    "tag_definition_id": 1,
                    "value": "a",
                }
            ]
        )
        assert flush.flush() == 1


class TestTagEntityJobBuilder:
    def test_payload_has_no_slice_keys(self):
        ts = TagSettings.from_dict(
            _settings_dict(mode="entity_based"), tag_key="demo/cap"
        )
        assert ts.validate().is_usable()
        scenario = Scenario.from_tag_settings(ts)
        jobs = TagEntityJobBuilder.build_backtest_engine_jobs(
            _enabled_tag_info(mode="entity_based"),
            scenario,
            entity_ids=["e1"],
        )
        payload = jobs[0]["payload"]
        assert BacktestJob.SLICE_BASED_ENTITY_KEY not in payload
        assert BacktestJob.TIMELINE_POINT_COUNT_KEY not in payload
        assert payload["entity_specified"] == [
            {"id": "e1", "start_date": "20240102", "end_date": "20240105"}
        ]


class TestTagEntityJobExecutor:
    def test_on_tick_buffers(self):
        ts = TagSettings.from_dict(
            _settings_dict(mode="entity_based"), tag_key="demo/cap"
        )
        ts.apply_defaults()
        runtime = TagHookRuntime(_EchoHooks(), tag_name="cap", settings=ts)
        definition = TagDefinition.from_dict(
            {"id": 7, "name": "tier", "scenario_id": 1}
        )
        contract = MagicMock()
        contract.get_entity_data.side_effect = lambda eid: [
            {"date": "20240102", "open": 1, "high": 1, "low": 1, "close": 1}
        ]
        state = EntityTaskState(
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
        ctx = MagicMock()
        ctx.init = {TagEntityJobExecutor._STATE_KEY: state}
        ctx.payload = {}
        sliced = {
            "e1": {
                "stock.kline.daily": [
                    {"date": "20240102", "open": 1, "high": 1, "low": 1, "close": 1}
                ]
            }
        }
        with patch(
            "core.modules.tag.core.engines.entity_based.executor.AsOfSlice.slice_contracts",
            return_value=sliced,
        ):
            TagEntityJobExecutor.on_tick(ctx, "20240102", 0)
        assert len(state.tag_values) == 1
        assert state.tag_values[0]["value"] == "e1:tier"


class TestTagSlicePipeline:
    def test_run_wires_be_and_flush(self):
        ts = TagSettings.from_dict(_settings_dict(), tag_key="demo/cap")
        assert ts.validate().is_usable()
        scenario = Scenario.from_tag_settings(ts)
        scenario.tag_definitions[0].id = 9

        def fake_run(jobs, **kwargs):
            cb = kwargs.get("callbacks")
            if cb and cb.on_task_result:
                cb.on_task_result(
                    JobReport(
                        job_id="tag_run",
                        success=True,
                        data={
                            "tag_values": [
                                {
                                    "entity_id": "e1",
                                    "as_of_date": "20240102",
                                    "tag_definition_id": 9,
                                    "value": "mid",
                                }
                            ]
                        },
                    ),
                    RunProgress(finished=1, total=1, ok=1, fail=0),
                )
            return MagicMock()

        with patch.object(TagSliceJobBuilder, "_count_open_dates", return_value=2), patch(
            "core.modules.tag.core.engines.slice_based.pipeline.BacktestEngine"
        ) as be:
            be.slice_based.run.side_effect = fake_run
            result = TagSlicePipeline.run(
                tag_info=_enabled_tag_info(),
                scenario=scenario,
                entity_ids=["e1"],
                dry_run=True,
            )
        assert result["success"] is True
        assert result["tag_values_count"] == 1
        assert result["saved_tag_values"] == 1
        assert result["dry_run"] is True
        be.slice_based.run.assert_called_once()
        call_kwargs = be.slice_based.run.call_args.kwargs
        assert call_kwargs.get("start")
        assert call_kwargs.get("callbacks") is not None

    def test_incremental_marks_progress_on_success(self):
        raw = _settings_dict()
        raw["calculation"]["update_mode"] = "incremental"
        raw["calculation"]["recompute"] = False
        info = _enabled_tag_info()
        info.settings = raw
        ts = TagSettings.from_dict(raw, tag_key="demo/cap")
        assert ts.validate().is_usable()
        scenario = Scenario.from_tag_settings(ts)
        scenario.tag_definitions[0].id = 9
        tags = MagicMock()
        tags.get_entity_calc_progress.return_value = {}

        def fake_run(jobs, **kwargs):
            cb = kwargs.get("callbacks")
            if cb and cb.on_task_result:
                cb.on_task_result(
                    JobReport(
                        job_id="tag_run",
                        success=True,
                        data={"tag_values": []},
                    ),
                    RunProgress(finished=1, total=1, ok=1, fail=0),
                )
            return MagicMock()

        with patch.object(TagSliceJobBuilder, "_count_open_dates", return_value=2), patch(
            "core.modules.tag.core.engines.slice_based.pipeline.BacktestEngine"
        ) as be:
            be.slice_based.run.side_effect = fake_run
            result = TagSlicePipeline.run(
                tag_info=info,
                scenario=scenario,
                entity_ids=["e1"],
                tag_data_service=tags,
                dry_run=False,
            )
        assert result["success"] is True
        tags.mark_entity_calc_progress.assert_called_once()
        args = tags.mark_entity_calc_progress.call_args.args
        assert args[0] == "demo/cap"
        assert args[1] == {"e1": "20240105"}
