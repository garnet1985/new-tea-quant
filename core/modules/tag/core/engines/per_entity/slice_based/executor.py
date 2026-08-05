"""slice_based TagSliceJobExecutor — BE RunCallbacks；日业务与 per-task 状态。

消费者: TagSlicePipeline

本文件:
- TagSliceJobExecutor: on_before_task_start / on_tick / on_ticks_complete
- SliceTaskState: 挂在 ``job_context.init`` 的可变袋

边界:
- 负责: AsOfSlice → hooks → buffer tag_values；本轮不写 DB
- 不负责: 片窗装载 / reader / queue / 进度（BE ``SliceOrchestrator``）
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Optional

from core.modules.backtest_engine.contracts import RunCallbacks
from core.modules.strategy.core.engines.shared.services.as_of_slice import AsOfSlice
from core.modules.strategy.core.services.entity_loader.job_bundle_loader import (
    JobBundleLoader,
)
from core.modules.tag.core.data_class.tag_definition import TagDefinition
from core.modules.tag.core.engines.shared.data_class.calendar_as_of import (
    TagCalendarAsOfResult,
)
from core.modules.tag.core.engines.shared.hooks.hook_params import TagContext
from core.modules.tag.core.engines.shared.hooks.runtime import TagHookRuntime
from core.modules.tag.core.engines.shared.tag_settings.tag_settings import TagSettings

logger = logging.getLogger(__name__)


@dataclass
class SliceTaskState:
    """单 task 可变业务状态，存于 ``job_context.init``。

    调度（窗宽 / reader / queue / 进度）由 BE ``SliceOrchestrator`` 持有，本类不感知。
    """

    entity_ids: List[str]
    settings: TagSettings
    hook_runtime: TagHookRuntime
    tag_name: str
    tag_path: str
    tag_definitions: List[TagDefinition]
    entity_contracts: Dict[str, Any]
    global_data: Dict[str, Any]
    payload: Dict[str, Any]
    tag_values: List[Dict[str, Any]] = field(default_factory=list)
    _ctx_base: TagContext = field(init=False, repr=False)
    _base_data_key: str = field(init=False, repr=False)
    _min_required: int = field(init=False, repr=False)
    _entity_window: Dict[str, tuple] = field(
        default_factory=dict, init=False, repr=False
    )
    _ready_date_by_entity: Dict[str, str] = field(
        default_factory=dict, init=False, repr=False
    )
    _job_min_ready_date: str = field(default="", init=False, repr=False)
    _uses_calendar_asof: bool = field(default=False, init=False, repr=False)
    _session_state: Dict[str, Any] = field(default_factory=dict, init=False, repr=False)
    _contracts_token: int = field(default=0, init=False, repr=False)

    def __post_init__(self) -> None:
        ids = [str(eid).strip() for eid in self.entity_ids if str(eid).strip()]
        self.entity_ids = ids
        self._base_data_key = self.settings.data.base_data_key
        self._min_required = max(int(self.settings.data.min_required_records or 0), 0) or 1
        self._uses_calendar_asof = self.hook_runtime.is_overridden("on_calendar_asof")
        self._entity_window = self._parse_entity_windows(self.payload)
        self._ctx_base = TagContext.assemble(
            tag_key=self.tag_name,
            settings=self.settings,
            entity_list=ids,
            tag_path=self.tag_path,
            custom={},
        )
        self._contracts_token = id(self.entity_contracts) if self.entity_contracts else 0
        self._refresh_ready_dates()

    @staticmethod
    def _parse_entity_windows(payload: Dict[str, Any]) -> Dict[str, tuple]:
        out: Dict[str, tuple] = {}
        for item in (payload or {}).get("entity_specified") or []:
            if not isinstance(item, dict):
                continue
            eid = str(item.get("id") or "").strip()
            if not eid:
                continue
            start = str(item.get("start_date") or "").strip()
            end = str(item.get("end_date") or "").strip()
            out[eid] = (start, end)
        return out

    def entity_in_calc_window(self, entity_id: str, as_of: str) -> bool:
        """实体在 payload 计算窗内才参与该 as_of（incremental 裁窗）。"""
        win = self._entity_window.get(entity_id)
        if not win:
            return True
        start, end = win
        day = str(as_of or "").strip()
        if start and day < start:
            return False
        if end and day > end:
            return False
        return True

    def bind_loaded_contracts(
        self,
        entity_contracts: Dict[str, Any],
        *,
        global_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Consume BE-loaded contracts for the current formal window."""
        token = id(entity_contracts)
        if token == self._contracts_token and entity_contracts is self.entity_contracts:
            return
        self.entity_contracts = (
            entity_contracts if isinstance(entity_contracts, dict) else {}
        )
        self._contracts_token = token
        if global_data is not None and isinstance(global_data, dict):
            self.global_data = global_data
        self._refresh_ready_dates()

    def _refresh_ready_dates(self) -> None:
        if not self.entity_contracts:
            self._ready_date_by_entity = {}
            self._job_min_ready_date = ""
            return
        base_contract = self.entity_contracts.get(self._base_data_key)
        self._ready_date_by_entity = AsOfSlice.ready_date_by_entity(
            base_contract,
            self.entity_ids,
            min_required=self._min_required,
        )
        self._job_min_ready_date = AsOfSlice.job_min_ready_date(
            self._ready_date_by_entity
        )

    @classmethod
    def from_job_context(cls, job_context: Any) -> "SliceTaskState":
        payload = job_context.payload or {}
        loaded = job_context.init or {}
        tag_info = payload.get("tag_info") or {}
        settings = TagSettings.from_dict(
            payload.get("settings") or {},
            tag_key=str(payload.get("scenario_name") or tag_info.get("key") or ""),
        )
        settings.apply_defaults()
        hook_runtime, err = TagHookRuntime.from_tag_info(tag_info, settings)
        if err is not None or hook_runtime is None:
            raise RuntimeError((err or {}).get("error") or "缺少hooks信息")

        entity_ids = [
            str(item.get("id") or "").strip()
            for item in (payload.get("entity_specified") or [])
            if str(item.get("id") or "").strip()
        ]
        if not entity_ids:
            entity_ids = [
                str(x).strip()
                for x in (payload.get("entity_ids") or [])
                if str(x).strip()
            ]

        definitions: List[TagDefinition] = []
        for raw in payload.get("tag_definitions") or []:
            if isinstance(raw, dict):
                definitions.append(TagDefinition.from_dict(raw))

        return cls(
            entity_ids=entity_ids,
            settings=settings,
            hook_runtime=hook_runtime,
            tag_name=str(tag_info.get("key") or ""),
            tag_path=str(tag_info.get("unique_relative_path") or ""),
            tag_definitions=definitions,
            entity_contracts=loaded.get("entity_contracts") or {},
            global_data=loaded.get("global_data") or {},
            payload=payload,
        )

    def buffer_tag_value(
        self,
        *,
        entity_id: str,
        as_of: str,
        tag_definition: TagDefinition,
        result: Dict[str, Any],
    ) -> None:
        value = result.get("value")
        if value is None:
            return
        self.tag_values.append(
            {
                "entity_id": entity_id,
                "as_of_date": as_of,
                "tag_definition_id": tag_definition.id,
                "tag_name": tag_definition.name,
                "value": value,
                "start_date": result.get("start_date"),
                "end_date": result.get("end_date"),
            }
        )

    def buffer_calendar_entity_tags(
        self,
        *,
        as_of: str,
        entity_tags: Dict[str, List[Dict[str, Any]]],
    ) -> None:
        by_name = {d.name: d for d in self.tag_definitions}
        for entity_id, items in (entity_tags or {}).items():
            eid = str(entity_id or "").strip()
            if not eid:
                continue
            if not self.entity_in_calc_window(eid, as_of):
                continue
            for item in items or []:
                if not isinstance(item, dict):
                    continue
                tag_name = str(item.get("tag_name") or "").strip()
                definition = by_name.get(tag_name)
                if definition is None:
                    logger.warning(
                        "on_calendar_asof unknown tag_name=%r entity=%s",
                        tag_name,
                        eid,
                    )
                    continue
                self.buffer_tag_value(
                    entity_id=eid,
                    as_of=as_of,
                    tag_definition=definition,
                    result=item,
                )


class TagSliceJobExecutor:
    """slice_based Tag JobExecutor。"""

    task_log_label: str = "tag_slice_task"
    _STATE_KEY: ClassVar[str] = "_tag_slice_state"

    @classmethod
    def build_run_callbacks(cls) -> RunCallbacks:
        return RunCallbacks(
            on_before_task_start=cls.on_before_task_start,
            on_tick=cls.on_tick,
            on_ticks_complete=cls.on_ticks_complete,
        )

    @classmethod
    def on_before_task_start(cls, job_context: Any) -> Dict[str, Any]:
        """Globals + business state only; per-entity IO is owned by BE orchestrator."""
        logger.info(
            "%s开始：job_id=%s（globals only）",
            cls.task_log_label,
            job_context.job_id,
        )
        global_data = JobBundleLoader.load_globals(job_context.payload or {})
        loaded: Dict[str, Any] = {
            "entity_contracts": {},
            "global_data": global_data,
        }
        job_context.init = loaded
        state = SliceTaskState.from_job_context(job_context)
        loaded[cls._STATE_KEY] = state
        logger.info(
            "%s就绪：global_keys=%d definitions=%d",
            cls.task_log_label,
            len(global_data),
            len(state.tag_definitions),
        )
        return loaded

    @classmethod
    def _state(cls, job_context: Any) -> SliceTaskState:
        init = job_context.init or {}
        state = init.get(cls._STATE_KEY)
        if state is None:
            state = SliceTaskState.from_job_context(job_context)
            init[cls._STATE_KEY] = state
            job_context.init = init
        return state

    @classmethod
    def on_tick(cls, job_context: Any, point: str, index: int) -> None:
        """BE 日历点 → bind contracts → AsOfSlice → hooks。"""
        _ = index
        init = job_context.init
        if not isinstance(init, dict):
            raise TypeError("job_context.init 必须是 dict（on_before_task_start 返回值）")
        state = cls._state(job_context)
        state.bind_loaded_contracts(
            init.get("entity_contracts") or {},
            global_data=init.get("global_data"),
        )
        as_of = str(point or "").strip()
        if not as_of:
            return
        if state._job_min_ready_date and as_of < state._job_min_ready_date:
            return

        sliced_by_entity = AsOfSlice.slice_contracts(state.entity_contracts, as_of)
        if state._uses_calendar_asof:
            cls._tick_calendar_asof(state, as_of=as_of, sliced_by_entity=sliced_by_entity)
        else:
            cls._tick_per_entity(state, as_of=as_of, sliced_by_entity=sliced_by_entity)

    @classmethod
    def _tick_calendar_asof(
        cls,
        state: SliceTaskState,
        *,
        as_of: str,
        sliced_by_entity: Dict[str, Dict[str, Any]],
    ) -> None:
        stocks_ctx = cls._build_stocks_context(state, sliced_by_entity, as_of=as_of)
        calendar = {
            "as_of_date": as_of,
            "session_state": dict(state._session_state),
        }
        asof_ctx = TagContext.fill(
            state._ctx_base,
            now=as_of,
            by_entity=stocks_ctx,
            calendar=calendar,
        )
        try:
            asof_result = state.hook_runtime.call("on_calendar_asof", asof_ctx)
        except Exception as exc:
            logger.error(
                "on_calendar_asof 失败：as_of=%s error=%s", as_of, exc, exc_info=True
            )
            return
        if not isinstance(asof_result, TagCalendarAsOfResult):
            raise TypeError(
                f"on_calendar_asof 必须返回 TagCalendarAsOfResult，"
                f"实际: {type(asof_result).__name__}"
            )
        state._session_state = dict(asof_result.session_state or {})
        state.buffer_calendar_entity_tags(
            as_of=as_of, entity_tags=asof_result.entity_tags or {}
        )

    @classmethod
    def _tick_per_entity(
        cls,
        state: SliceTaskState,
        *,
        as_of: str,
        sliced_by_entity: Dict[str, Dict[str, Any]],
    ) -> None:
        for entity_id in state.entity_ids:
            if not state.entity_in_calc_window(entity_id, as_of):
                continue
            ready = state._ready_date_by_entity.get(entity_id) or ""
            if (not ready) or as_of < ready:
                continue
            per_entity = sliced_by_entity.get(entity_id, {})
            bar = AsOfSlice.base_bar(
                per_entity,
                base_data_key=state._base_data_key,
                as_of=as_of,
                min_required=state._min_required,
            )
            if bar is None:
                continue
            complete_data = dict(per_entity)
            if state.global_data:
                complete_data = {**state.global_data, **per_entity}
            for definition in state.tag_definitions:
                scan_ctx = TagContext.fill(
                    state._ctx_base,
                    now=as_of,
                    items=complete_data,
                    entity_id=entity_id,
                    entity_info={"id": entity_id},
                    tag_definition=definition,
                )
                try:
                    result = state.hook_runtime.call("calculate_tag", scan_ctx)
                except Exception as exc:
                    logger.error(
                        "calculate_tag 失败：entity=%s as_of=%s tag=%s error=%s",
                        entity_id,
                        as_of,
                        definition.name,
                        exc,
                        exc_info=True,
                    )
                    continue
                if isinstance(result, dict):
                    state.buffer_tag_value(
                        entity_id=entity_id,
                        as_of=as_of,
                        tag_definition=definition,
                        result=result,
                    )

    @classmethod
    def _build_stocks_context(
        cls,
        state: SliceTaskState,
        sliced_by_entity: Dict[str, Dict[str, Any]],
        *,
        as_of: str,
    ) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for entity_id in state.entity_ids:
            if not state.entity_in_calc_window(entity_id, as_of):
                continue
            ready = state._ready_date_by_entity.get(entity_id) or ""
            if (not ready) or as_of < ready:
                continue
            per_entity = sliced_by_entity.get(entity_id, {})
            bar = AsOfSlice.base_bar(
                per_entity,
                base_data_key=state._base_data_key,
                as_of=as_of,
                min_required=state._min_required,
            )
            if bar is None:
                continue
            complete_data = dict(per_entity)
            if state.global_data:
                complete_data = {**state.global_data, **per_entity}
            out[entity_id] = complete_data
        return out

    @classmethod
    def on_ticks_complete(cls, job_context: Any, timeline: Any) -> Dict[str, Any]:
        _ = timeline
        state = cls._state(job_context)
        count = len(state.tag_values)
        logger.info(
            "tag slice 执行完成：tag_values_count=%d entities=%d",
            count,
            len(state.entity_ids),
        )
        return {
            "success": True,
            "tag_values_count": count,
            "entities_count": len(state.entity_ids),
            "tag_values": list(state.tag_values),
        }


__all__ = ["TagSliceJobExecutor", "SliceTaskState"]
