"""Tag calendar_slice 单元测试。"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from core.modules.tag.engines.shared.base_worker import BaseTagWorker
from core.modules.tag.engines.sliced.runtime.compute_engine import TagSliceComputeEngine
from core.modules.tag.engines.sliced.load_range import tag_slice_load_start
from core.modules.tag.engines.sliced.slice_job import build_tag_calendar_slice_job
from core.modules.tag.enums import TagExecutionMode, TagUpdateMode
from core.modules.tag.models.scenario_model import ScenarioModel
from core.modules.tag.settings.normalize import normalize_tag_settings
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.messages import (
    SlicePayload,
)

_STOCK_KLINE = {"data_id": "stock.kline.daily", "params": {"adjust": "qfq"}}


def _refresh_calendar_settings(**overrides):
    base = {
        "is_enabled": True,
        "meta": {"display_name": "slice"},
        "calculation": {
            "update_mode": "refresh",
            "recompute": True,
            "execution_mode": "calendar_slice",
            "start_date": "20240101",
            "end_date": "20240131",
        },
        "data": {
            "base_required_data": _STOCK_KLINE,
            "extra_required_data_sources": [],
            "min_required_records": 20,
        },
        "tags": [{"name": "tag1"}],
    }
    for key, value in overrides.items():
        if key in ("calculation", "data", "meta") and isinstance(value, dict):
            base[key] = {**base.get(key, {}), **value}
        else:
            base[key] = value
    return base


class TestTagExecutionModeSettings:
    def test_calendar_slice_valid_with_recompute(self):
        assert ScenarioModel.is_setting_valid(
            normalize_tag_settings(_refresh_calendar_settings(), tag_key="slice_scenario")
        ) is True

    def test_calendar_slice_rejects_incremental_without_recompute(self):
        settings = _refresh_calendar_settings(
            calculation={"recompute": False, "update_mode": "incremental"},
        )
        assert ScenarioModel.is_setting_valid(
            normalize_tag_settings(settings, tag_key="slice_scenario")
        ) is False

    def test_calendar_slice_rejects_non_timeseries_base(self):
        settings = _refresh_calendar_settings(
            data={
                "base_required_data": {"data_id": "stock.list", "params": {}},
                "min_required_records": 0,
            },
        )
        with pytest.raises(ValueError):
            normalize_tag_settings(settings, tag_key="slice_scenario")

    def test_calendar_slice_rejects_forbidden_performance_keys(self):
        settings = _refresh_calendar_settings(
            performance={"entities_per_job": 100},
        )
        assert ScenarioModel.is_setting_valid(
            normalize_tag_settings(settings, tag_key="slice_scenario")
        ) is False


class TestTagSliceJob:
    def test_build_tag_calendar_slice_job(self):
        raw = _refresh_calendar_settings()
        scenario = ScenarioModel.create_from_settings(raw, tag_key="slice_scenario")
        payload = build_tag_calendar_slice_job(
            entity_ids=["000001", "000002"],
            settings=scenario.get_settings(),
            scenario_model=scenario,
            worker_module_path="userspace.extensions.tags.demo.tag_worker",
            worker_class_name="DemoTagWorker",
            global_extra_cache={},
        )
        assert payload["tag_execution_mode"] == TagExecutionMode.CALENDAR_SLICE.value
        assert payload["slice_open_days"] == "auto"
        assert payload["entity_ids"] == ["000001", "000002"]
        assert payload["update_mode"] == TagUpdateMode.REFRESH
        assert len(payload["entities"]) == 2

    def test_build_rejects_non_refresh(self):
        raw = {
            "is_enabled": True,
            "calculation": {
                "update_mode": "incremental",
                "execution_mode": "entity_timeline",
                "start_date": "20240101",
                "end_date": "20240131",
            },
            "data": {
                "base_required_data": _STOCK_KLINE,
                "min_required_records": 5,
            },
            "tags": [{"name": "t"}],
        }
        scenario = ScenarioModel.create_from_settings(raw, tag_key="x")
        with pytest.raises(ValueError, match="REFRESH"):
            build_tag_calendar_slice_job(
                entity_ids=["000001"],
                settings=scenario.get_settings(),
                scenario_model=scenario,
                worker_module_path="m",
                worker_class_name="C",
                global_extra_cache={},
            )


def test_tag_slice_load_start_uses_lookback():
    payload = {"settings": {"incremental_required_records_before_as_of_date": 30}}
    start = tag_slice_load_start("20240115", payload)
    assert start < "20240115"


def test_tag_compute_engine_accumulates_tag_values():
    job_payload = {
        "entity_ids": ["000001"],
        "slice_open_days": 50,
        "entity_type": "stock_kline_daily",
        "scenario_name": "s",
        "update_mode": TagUpdateMode.REFRESH,
        "tag_definitions": [],
        "settings": {},
        "worker_module_path": "mod",
        "worker_class_name": "W",
        "global_extra_cache": {},
        "start_date": "20240101",
        "end_date": "20240131",
    }
    fake_result = {
        "success": True,
        "tag_values": [{"entity_id": "000001", "as_of_date": "20240102"}],
        "errors": [],
    }
    payload = SlicePayload(
        slice_id="slice_0",
        slice_index=0,
        window_start="20240102",
        window_end="20240102",
        open_dates=("20240102",),
        batch_transfer={
            "by_entity": {
                "000001": {
                    "slot_data": {},
                    "trading_dates": ["20240102"],
                    "prior_tag_values": {},
                }
            }
        },
    )

    class _PerEntityWorker(BaseTagWorker):
        def calculate_tag(self, as_of_date, historical_data, tag_definition):
            return None

    with patch.object(
        TagSliceComputeEngine,
        "_resolve_worker_class",
        return_value=_PerEntityWorker,
    ):
        engine = TagSliceComputeEngine(job_payload)
        with patch.object(
            TagSliceComputeEngine,
            "_run_worker_for_payload",
            return_value=fake_result,
        ):
            slice_rows = engine.run_slice(payload)
        summary = engine.finalize_all()
    assert slice_rows == fake_result["tag_values"]
    assert summary["total_tags"] == 1
    assert summary["tag_values"] == []


def test_tag_compute_engine_drains_slice_tag_values_between_slices():
    job_payload = {
        "entity_ids": ["000001"],
        "slice_open_days": 50,
        "entity_type": "stock_kline_daily",
        "scenario_name": "s",
        "update_mode": TagUpdateMode.REFRESH,
        "tag_definitions": [],
        "settings": {},
        "worker_module_path": "mod",
        "worker_class_name": "W",
        "global_extra_cache": {},
        "start_date": "20240101",
        "end_date": "20240131",
    }

    class _PerEntityWorker(BaseTagWorker):
        def calculate_tag(self, as_of_date, historical_data, tag_definition):
            return None

    def _payload(as_of: str) -> SlicePayload:
        return SlicePayload(
            slice_id=f"slice_{as_of}",
            slice_index=0,
            window_start=as_of,
            window_end=as_of,
            open_dates=(as_of,),
            batch_transfer={
                "by_entity": {
                    "000001": {
                        "slot_data": {},
                        "trading_dates": [as_of],
                        "prior_tag_values": {},
                    }
                }
            },
        )

    with patch.object(
        TagSliceComputeEngine,
        "_resolve_worker_class",
        return_value=_PerEntityWorker,
    ):
        engine = TagSliceComputeEngine(job_payload)
        with patch.object(
            TagSliceComputeEngine,
            "_run_worker_for_payload",
            side_effect=[
                {"success": True, "tag_values": [{"entity_id": "000001", "as_of_date": "20240102"}], "errors": []},
                {"success": True, "tag_values": [{"entity_id": "000001", "as_of_date": "20240103"}], "errors": []},
            ],
        ):
            first = engine.run_slice(_payload("20240102"))
            second = engine.run_slice(_payload("20240103"))
        summary = engine.finalize_all()

    assert first[0]["as_of_date"] == "20240102"
    assert second[0]["as_of_date"] == "20240103"
    assert summary["total_tags"] == 2
    assert summary["tag_values"] == []


def test_profile_calendar_slice_config_for_tag():
    from core.modules.tag.settings.normalize import profile_tag_calendar_slice_config

    cfg = profile_tag_calendar_slice_config()
    assert cfg.get("reader_workers") == "auto"
    assert cfg.get("prefetch_enabled") is True
