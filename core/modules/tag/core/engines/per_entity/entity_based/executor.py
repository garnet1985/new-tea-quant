"""entity_based TagEntityJobExecutor — BE RunCallbacks。

消费者: TagEntityPipeline

本文件:
- TagEntityJobExecutor / EntityTaskState
  边界: AsOfSlice → per-entity calculate_tag → buffer；不负责落库
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List

from core.modules.backtest_engine.contracts import RunCallbacks
from core.modules.strategy.contracts import AsOfSlice, JobBundleLoader
from core.modules.tag.core.data_class.tag_definition import TagDefinition
from core.modules.tag.core.engines.shared.hooks.hook_params import TagContext
from core.modules.tag.core.engines.shared.hooks.runtime import TagHookRuntime
from core.modules.tag.core.engines.shared.tag_settings.tag_settings import TagSettings

logger = logging.getLogger(__name__)


@dataclass
class EntityTaskState:
    """单 task 可变状态（挂在 ``job_context.init``）。"""

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
    entity_start_by_id: Dict[str, str] = field(default_factory=dict)
    entity_end_by_id: Dict[str, str] = field(default_factory=dict)
    # entity_id -> {tag_definition_id|str name -> scalar prior}
    prior_by_entity: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    _ctx_base: TagContext = field(init=False, repr=False)
    _base_data_key: str = field(init=False, repr=False)
    _min_required: int = field(init=False, repr=False)
    _ready_date_by_entity: Dict[str, str] = field(
        default_factory=dict, init=False, repr=False
    )
    _job_min_ready_date: str = field(default="", init=False, repr=False)

    def __post_init__(self) -> None:
        ids = [str(eid).strip() for eid in self.entity_ids if str(eid).strip()]
        self.entity_ids = ids
        self._base_data_key = self.settings.data.base_data_key
        self._min_required = max(int(self.settings.data.min_required_records or 0), 0) or 1
        self._ctx_base = TagContext.assemble(
            tag_key=self.tag_name,
            settings=self.settings,
            entity_list=ids,
            tag_path=self.tag_path,
            custom={},
        )
        base_contract = self.entity_contracts.get(self._base_data_key)
        self._ready_date_by_entity = AsOfSlice.ready_date_by_entity(
            base_contract,
            ids,
            min_required=self._min_required,
        )
        self._job_min_ready_date = AsOfSlice.job_min_ready_date(
            self._ready_date_by_entity
        )

    @classmethod
    def from_job_context(cls, job_context: Any) -> "EntityTaskState":
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

        entity_ids: List[str] = []
        entity_start_by_id: Dict[str, str] = {}
        entity_end_by_id: Dict[str, str] = {}
        for item in payload.get("entity_specified") or []:
            if not isinstance(item, dict):
                continue
            eid = str(item.get("id") or "").strip()
            if not eid:
                continue
            entity_ids.append(eid)
            start = str(item.get("start_date") or "").strip()
            end = str(item.get("end_date") or "").strip()
            if start:
                entity_start_by_id[eid] = start
            if end:
                entity_end_by_id[eid] = end
        definitions: List[TagDefinition] = []
        for raw in payload.get("tag_definitions") or []:
            if isinstance(raw, dict):
                definitions.append(TagDefinition.from_dict(raw))

        raw_priors = payload.get("prior_tag_values") or {}
        prior_by_entity: Dict[str, Dict[str, Any]] = {}
        if isinstance(raw_priors, dict):
            for eid, by_tag in raw_priors.items():
                key = str(eid or "").strip()
                if key and isinstance(by_tag, dict):
                    prior_by_entity[key] = dict(by_tag)

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
            entity_start_by_id=entity_start_by_id,
            entity_end_by_id=entity_end_by_id,
            prior_by_entity=prior_by_entity,
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


class TagEntityJobExecutor:
    """entity_based Tag JobExecutor。"""

    task_log_label: str = "tag_entity_task"
    _STATE_KEY: ClassVar[str] = "_tag_entity_state"

    @classmethod
    def build_run_callbacks(cls) -> RunCallbacks:
        return RunCallbacks(
            on_before_task_start=cls.on_before_task_start,
            on_tick=cls.on_tick,
            on_ticks_complete=cls.on_ticks_complete,
        )

    @classmethod
    def on_before_task_start(cls, job_context: Any) -> Dict[str, Any]:
        logger.info("%s开始：job_id=%s", cls.task_log_label, job_context.job_id)
        loaded = JobBundleLoader.load(job_context.payload or {})
        job_context.init = loaded
        state = EntityTaskState.from_job_context(job_context)
        loaded[cls._STATE_KEY] = state
        return loaded

    @classmethod
    def _state(cls, job_context: Any) -> EntityTaskState:
        init = job_context.init or {}
        state = init.get(cls._STATE_KEY)
        if state is None:
            state = EntityTaskState.from_job_context(job_context)
            init[cls._STATE_KEY] = state
            job_context.init = init
        return state

    @classmethod
    def on_tick(cls, job_context: Any, point: str, index: int) -> None:
        state = cls._state(job_context)
        as_of = str(point or "").strip()
        if not as_of:
            return
        if state._job_min_ready_date and as_of < state._job_min_ready_date:
            return

        sliced_by_entity = AsOfSlice.slice_contracts(state.entity_contracts, as_of)
        for entity_id in state.entity_ids:
            entity_start = state.entity_start_by_id.get(entity_id) or ""
            if entity_start and as_of < entity_start:
                continue
            entity_end = state.entity_end_by_id.get(entity_id) or ""
            if entity_end and as_of > entity_end:
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
                prior = None
                by_tag = state.prior_by_entity.get(entity_id) or {}
                if definition.id is not None:
                    prior = by_tag.get(str(int(definition.id)))
                if prior is None and definition.name:
                    prior = by_tag.get(str(definition.name))
                scan_ctx = TagContext.fill(
                    state._ctx_base,
                    now=as_of,
                    items=complete_data,
                    entity_id=entity_id,
                    entity_info={"id": entity_id},
                    tag_definition=definition,
                    prior_value=prior,
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
    def on_ticks_complete(cls, job_context: Any, timeline: Any) -> Dict[str, Any]:
        state = cls._state(job_context)
        count = len(state.tag_values)
        logger.info(
            "tag entity 执行完成：tag_values_count=%d entities=%d",
            count,
            len(state.entity_ids),
        )
        return {
            "success": True,
            "tag_values_count": count,
            "entities_count": len(state.entity_ids),
            "tag_values": list(state.tag_values),
        }


__all__ = ["TagEntityJobExecutor"]
