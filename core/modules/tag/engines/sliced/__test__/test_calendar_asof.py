"""Tag calendar_asof 与 entity_context 单元测试。"""
from __future__ import annotations

from unittest.mock import patch

from core.modules.tag.engines.shared.base_worker import BaseTagWorker
from core.modules.tag.engines.sliced.runtime.compute_engine import TagSliceComputeEngine
from core.modules.tag.engines.sliced.entity_context import build_entity_historical_context, build_entity_contexts, EntityDataContext
from core.modules.tag.engines.sliced.types import TagCalendarAsOfResult
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.messages import (
    SlicePayload,
)


class _CalendarTagWorker(BaseTagWorker):
    def calculate_tag(self, as_of_date, historical_data, tag_definition):
        return None

    def on_calendar_asof(self, ctx, settings):
        _ = settings
        carry = dict(ctx.carry or {})
        carry["seen"] = carry.get("seen", 0) + 1
        entity_tags = {}
        if ctx.as_of_date == "20240201" and "000001" in ctx.stocks:
            entity_tags["000001"] = [{"tag_name": "tag1", "value": "picked"}]
        return TagCalendarAsOfResult(entity_tags=entity_tags, carry=carry)


def test_build_entity_historical_context_filters_by_as_of():
    by_entity = {
        "A": {
            "slot_data": {
                "stock.kline.daily": [
                    {"date": "20240101", "close": 1.0},
                    {"date": "20240102", "close": 2.0},
                ],
            },
            "time_field_overrides": {"stock.kline.daily": "date"},
        },
        "B": {
            "slot_data": {
                "stock.kline.daily": [{"date": "20240101", "close": 3.0}],
            },
            "time_field_overrides": {"stock.kline.daily": "date"},
        },
    }
    
    # 使用新的 DataCursor 实现
    entity_contexts = build_entity_contexts(by_entity)
    entities = build_entity_historical_context(
        as_of="20240102",
        axis_data_id="stock.kline.daily",
        min_records=1,
        entity_contexts=entity_contexts,
    )
    
    assert "A" in entities
    assert "B" not in entities
    assert entities["A"]["stock.kline.daily"][-1]["date"] == "20240102"


def test_calendar_asof_fan_out_and_carry():
    job_payload = {
        "entity_ids": ["000001"],
        "slice_open_days": 50,
        "entity_type": "stock_kline_daily",
        "scenario_name": "s",
        "update_mode": "refresh",
        "tag_definitions": [{"id": 9, "name": "tag1", "tag_name": "tag1"}],
        "settings": {
            "data": {
                "required": [{"data_id": "stock.kline.daily", "params": {"adjust": "qfq"}}],
            },
            "incremental_required_records_before_as_of_date": 1,
        },
        "worker_module_path": __name__,
        "worker_class_name": "_CalendarTagWorker",
        "global_extra_cache": {},
        "start_date": "20240101",
        "end_date": "20240131",
        "backtest_calendar": {
            "open_dates": ["20240102", "20240201"],
        },
    }
    payload = SlicePayload(
        slice_id="slice_0",
        slice_index=0,
        window_start="20240102",
        window_end="20240201",
        open_dates=("20240102", "20240201"),
        batch_transfer={
            "by_entity": {
                "000001": {
                    "slot_data": {
                        "stock.kline.daily": [
                            {"date": "20240102", "close": 1.0},
                            {"date": "20240201", "close": 1.1},
                        ],
                    },
                    "trading_dates": ["20240102", "20240201"],
                    "time_field_overrides": {"stock.kline.daily": "date"},
                }
            }
        },
    )
    with patch.object(
        TagSliceComputeEngine,
        "_resolve_worker_class",
        return_value=_CalendarTagWorker,
    ):
        engine = TagSliceComputeEngine(job_payload)
        slice_rows = engine.run_slice(payload)
        summary = engine.finalize_all()

    assert summary["carry"]["seen"] == 2
    assert summary["total_tags"] == 1
    assert summary["tag_values"] == []
    assert len(slice_rows) == 1
    row = slice_rows[0]
    assert row["entity_id"] == "000001"
    assert row["as_of_date"] == "20240201"
    assert row["json_value"] == '{"value":"picked"}'
