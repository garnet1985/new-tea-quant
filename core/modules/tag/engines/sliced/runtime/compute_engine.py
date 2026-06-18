#!/usr/bin/env python3
"""Tag calendar_slice Compute Engine：per-entity 或 on_calendar_asof 横截面。"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple, Type

from core.modules.strategy.engines.shared.helpers.backtest_calendar_context import (
    BacktestCalendarContext,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.messages import (
    SlicePayload,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.slice_plan import (
    is_first_open_of_month,
    is_first_open_of_year,
    is_last_open_of_month,
    is_last_open_of_year,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.types import (
    CalendarAsOfContext,
)
from core.modules.tag.engines.shared.base_worker import BaseTagWorker, worker_uses_calendar_asof
from core.modules.tag.engines.sliced.stocks_context import (
    axis_data_id_from_settings,
    build_stocks_context,
)
from core.modules.tag.engines.shared.staging.prior_values import encode_tag_json_value
from core.modules.tag.engines.sliced.types import TagCalendarAsOfResult
from core.modules.tag.models.tag_model import TagModel

logger = logging.getLogger(__name__)

_CALENDAR_SLICE_ENTITY_ID = "__calendar_slice__"


class TagSliceComputeEngine:
    """消费 SlicePayload：横截面 on_calendar_asof 或逐 entity calculate_tag。"""

    def __init__(self, job_payload: Dict[str, Any]):
        self.job_payload = job_payload
        self.entity_ids = [
            str(e).strip() for e in (job_payload.get("entity_ids") or []) if str(e).strip()
        ]
        if not self.entity_ids:
            raise ValueError("TagSliceComputeEngine 缺少 entity_ids")
        raw_slice = job_payload.get("slice_open_days")
        if not isinstance(raw_slice, int):
            raise ValueError(
                f"tag compute lane 需要 orchestrator 已 resolve 的 slice_open_days 整数，"
                f"收到 {raw_slice!r}"
            )
        self._slice_open_days = raw_slice
        self._settings = dict(job_payload.get("settings") or {})
        self._entity_type = str(job_payload.get("entity_type") or "stock_kline_daily")
        self._tag_def_by_name = self._index_tag_definitions(
            job_payload.get("tag_definitions") or []
        )
        self._worker_class = self._resolve_worker_class(job_payload)
        self._uses_calendar_asof = worker_uses_calendar_asof(self._worker_class)
        self._carry: Dict[str, Any] = {}
        self._all_tag_values: List[Dict[str, Any]] = []
        self._errors: List[str] = []
        self._open_dates_all: Tuple[str, ...] = self._resolve_all_open_dates()

    def run_slice(self, payload: SlicePayload) -> None:
        if self._uses_calendar_asof:
            self._run_slice_calendar_asof(payload)
            return
        self._run_slice_per_entity(payload)

    def finalize_all(self) -> Dict[str, Any]:
        return {
            "success": not self._errors,
            "tag_values": list(self._all_tag_values),
            "total_tags": len(self._all_tag_values),
            "errors": list(self._errors),
            "entity_count": len(self.entity_ids),
            "carry": dict(self._carry),
        }

    def _run_slice_per_entity(self, payload: SlicePayload) -> None:
        by_entity = (payload.batch_transfer or {}).get("by_entity") or {}
        open_set = set(payload.open_dates)
        for eid in self.entity_ids:
            inject_root = by_entity.get(eid)
            if not isinstance(inject_root, dict):
                self._errors.append(f"missing inject slice for entity_id={eid}")
                continue
            trading_dates = [
                d for d in (inject_root.get("trading_dates") or []) if d in open_set
            ]
            if not trading_dates:
                continue
            slice_inject = {
                **inject_root,
                "trading_dates": trading_dates,
            }
            sub_payload = self._entity_sub_payload(eid, slice_inject)
            try:
                result = self._run_worker_for_payload(sub_payload)
                if not result.get("success", True):
                    self._errors.append(
                        f"entity_id={eid} slice={payload.slice_id}: compute failed"
                    )
                self._all_tag_values.extend(result.get("tag_values") or [])
                self._errors.extend(result.get("errors") or [])
            except Exception as exc:
                msg = f"entity_id={eid} slice={payload.slice_id}: {exc}"
                logger.exception("Tag slice compute entity failed: %s", msg)
                self._errors.append(msg)

    def _run_slice_calendar_asof(self, payload: SlicePayload) -> None:
        by_entity = (payload.batch_transfer or {}).get("by_entity") or {}
        settings = self._settings
        axis_id = axis_data_id_from_settings(settings)
        min_records = int(
            settings.get("incremental_required_records_before_as_of_date") or 1
        )
        worker = self._create_bulk_worker()

        for open_date_index, as_of in enumerate(payload.open_dates):
            stocks = build_stocks_context(
                by_entity,
                as_of,
                axis_data_id=axis_id,
                min_records=min_records,
            )
            ctx = CalendarAsOfContext(
                as_of_date=as_of,
                slice_id=payload.slice_id,
                slice_open_days=self._slice_open_days,
                window_start=payload.window_start,
                window_end=payload.window_end,
                stocks=stocks,
                carry=dict(self._carry),
                open_date_index=open_date_index,
                is_first_open_of_month=is_first_open_of_month(as_of, self._open_dates_all),
                is_last_open_of_month=is_last_open_of_month(as_of, self._open_dates_all),
                is_first_open_of_year=is_first_open_of_year(as_of, self._open_dates_all),
                is_last_open_of_year=is_last_open_of_year(as_of, self._open_dates_all),
            )
            try:
                asof_result = self._call_on_calendar_asof(worker, ctx, settings)
                self._carry = dict(asof_result.carry or {})
                self._append_entity_tags(as_of, asof_result)
            except Exception as exc:
                msg = f"on_calendar_asof slice={payload.slice_id} as_of={as_of}: {exc}"
                logger.exception("Tag calendar_asof failed: %s", msg)
                self._errors.append(msg)

    def _append_entity_tags(self, as_of: str, result: TagCalendarAsOfResult) -> None:
        for eid, writes in (result.entity_tags or {}).items():
            eid_s = str(eid or "").strip()
            if not eid_s:
                continue
            if not isinstance(writes, list):
                continue
            for item in writes:
                if not isinstance(item, dict):
                    continue
                tag_name = str(item.get("tag_name") or "").strip()
                tag_def = self._tag_def_by_name.get(tag_name)
                if tag_def is None:
                    self._errors.append(
                        f"unknown tag_name={tag_name!r} entity_id={eid_s} as_of={as_of}"
                    )
                    continue
                if "value" not in item:
                    continue
                self._all_tag_values.append(
                    {
                        "entity_id": eid_s,
                        "entity_type": self._entity_type,
                        "tag_definition_id": tag_def.id,
                        "as_of_date": as_of,
                        "json_value": encode_tag_json_value(item),
                        "start_date": item.get("start_date"),
                        "end_date": item.get("end_date"),
                    }
                )

    def _call_on_calendar_asof(
        self,
        worker: BaseTagWorker,
        ctx: CalendarAsOfContext,
        settings: Dict[str, Any],
    ) -> TagCalendarAsOfResult:
        raw = worker.on_calendar_asof(ctx, settings)
        if isinstance(raw, TagCalendarAsOfResult):
            return raw
        if isinstance(raw, dict):
            return TagCalendarAsOfResult(
                entity_tags=dict(raw.get("entity_tags") or {}),
                carry=dict(raw.get("carry") or {}),
            )
        raise TypeError(
            "on_calendar_asof 须返回 TagCalendarAsOfResult 或 "
            "{'entity_tags': ..., 'carry': ...} dict"
        )

    def _create_bulk_worker(self) -> BaseTagWorker:
        bulk = dict(self.job_payload)
        bulk["entity_id"] = _CALENDAR_SLICE_ENTITY_ID
        bulk["_inject"] = {
            "slot_data": {},
            "trading_dates": [],
            "prior_tag_values": {},
        }
        return self._worker_class(job_payload=bulk)

    def _entity_sub_payload(
        self,
        entity_id: str,
        inject_slice: Dict[str, Any],
    ) -> Dict[str, Any]:
        keys = (
            "entity_type",
            "scenario_name",
            "update_mode",
            "tag_definitions",
            "settings",
            "worker_module_path",
            "worker_class_name",
            "worker_file_path",
            "global_extra_cache",
            "start_date",
            "end_date",
        )
        sub = {key: self.job_payload[key] for key in keys if key in self.job_payload}
        sub["entity_id"] = entity_id
        sub["_inject"] = inject_slice
        return sub

    def _resolve_all_open_dates(self) -> Tuple[str, ...]:
        cal = BacktestCalendarContext.from_dict(self.job_payload.get("backtest_calendar"))
        if cal is None:
            return ()
        start = str(self.job_payload.get("start_date") or "")
        end = str(self.job_payload.get("end_date") or "")
        return tuple(d for d in cal.open_dates if start <= d <= end)

    @staticmethod
    def _index_tag_definitions(raw: List[Any]) -> Dict[str, TagModel]:
        out: Dict[str, TagModel] = {}
        for item in raw:
            if isinstance(item, dict):
                model = TagModel.from_dict(item)
            elif isinstance(item, TagModel):
                model = item
            else:
                continue
            name = str(model.get_name() or model.tag_name or "").strip()
            if name:
                out[name] = model
        return out

    @staticmethod
    def _resolve_worker_class(job_payload: Dict[str, Any]) -> Type[BaseTagWorker]:
        from core.modules.tag.services.discovery.worker_loader import import_tag_worker_class

        worker_module_path = job_payload.get("worker_module_path")
        worker_class_name = job_payload.get("worker_class_name")
        worker_file_path = str(job_payload.get("worker_file_path") or "")
        if not worker_module_path or not worker_class_name:
            raise ValueError(
                f"缺少 worker 模块信息: worker_module_path={worker_module_path}, "
                f"worker_class_name={worker_class_name}"
            )
        worker_class = import_tag_worker_class(
            worker_module_path=str(worker_module_path),
            worker_class_name=str(worker_class_name),
            worker_file_path=worker_file_path,
        )
        if not issubclass(worker_class, BaseTagWorker):
            raise TypeError(f"{worker_class_name} 须继承 BaseTagWorker")
        return worker_class

    @staticmethod
    def _run_worker_for_payload(job_payload: Dict[str, Any]) -> Dict[str, Any]:
        worker_class = TagSliceComputeEngine._resolve_worker_class(job_payload)
        worker = worker_class(job_payload=job_payload)
        return worker.process_entity()


__all__ = ["TagSliceComputeEngine"]
