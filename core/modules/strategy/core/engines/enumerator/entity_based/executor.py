"""entity_based EnumEntityJobExecutor — BE RunCallbacks；日业务与 per-task 状态。

本文件（entity 两件套之一，与 EnumEntityJobBuilder；见 ``BOUNDARY_NOTES.md``「与 BE 的关系」）:
- EnumEntityJobExecutor: on_before_task_start / on_tick / on_ticks_complete / flush
- EntityTaskState: 挂在 ``job_context.init`` 的可变袋（**不是**第二套 BE session）

边界:
- 负责: 经 callback 改写执行中的数据与逻辑
- 不负责: 建 jobs；覆盖 BE 默认日历轴；平行 session / TimelineBuilder
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.modules.backtest_engine.contracts import JobContext, Timeline
from core.modules.data_contract.contracts import DATA_KEY
from core.modules.strategy.core.engines.enumerator.common.base_executor import (
    BaseJobExecutor,
    ExecutorHooksContext,
)
from core.modules.strategy.core.engines.enumerator.common.performance_tracker.performance_tracker import (
    EnumJobPerfRecorder,
)
from core.modules.strategy.core.engines.enumerator.common.state.investment_tracker import (
    InvestmentTracker,
)
from core.modules.strategy.core.engines.shared.data_class import Opportunity
from core.modules.strategy.core.services.entity_loader.strategy_data_resolver import (
    StrategyDataResolver,
)
from core.modules.strategy.core.engines.shared.services.as_of_slice import AsOfSlice
from core.modules.strategy.core.engines.shared.services.safe_values.safe_bar_value import (
    SafeBarValue,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.helpers.stock_meta import StockMetaHelper
from core.modules.strategy.core.hooks.hook_params import StrategyContext, StrategyData

logger = logging.getLogger(__name__)

_STATE_KEY = "_entity_task_state"
_TIMELINE_KEY = "_entity_timeline"


@dataclass
class EntityTaskState:
    """单 task 可变状态，存于 ``job_context.init``（BE hold 的 init）。

    不是平行于 BE 的 session；仅是 Executor 在 init 袋里放的 trackers / contexts。
    """

    entity_ids: List[str]
    settings: StrategySettings
    hook_runtime: Any
    strategy_name: str
    entity_contracts: Dict[str, Any]
    global_data: Dict[str, Any]
    entity_specified: List[Dict[str, Any]]
    payload: Dict[str, Any]
    perf: Optional[EnumJobPerfRecorder] = None

    trackers: Dict[str, InvestmentTracker] = field(init=False)
    _stock_info: Dict[str, Dict[str, Any]] = field(init=False, repr=False)
    _last_bar_by_entity: Dict[str, Dict[str, Any]] = field(init=False, repr=False)
    _scan_contexts: Dict[str, StrategyContext] = field(init=False, repr=False)
    _base_data_key: str = field(init=False, repr=False)
    _min_required: int = field(init=False, repr=False)
    _timeline_points: tuple = field(default_factory=tuple, init=False, repr=False)
    _start_date: str = field(default="", init=False, repr=False)
    _end_date: str = field(default="", init=False, repr=False)
    _ready_date_by_entity: Dict[str, str] = field(
        default_factory=dict, init=False, repr=False
    )
    _job_min_ready_date: str = field(default="", init=False, repr=False)
    _job_has_work: bool = field(default=True, init=False, repr=False)

    def __post_init__(self) -> None:
        self.trackers = {
            str(entity_id).strip(): InvestmentTracker(entity_id=str(entity_id).strip())
            for entity_id in self.entity_ids
            if str(entity_id).strip()
        }
        self._stock_info = {
            entity_id: StockMetaHelper.load(entity_id) for entity_id in self.trackers
        }
        self._last_bar_by_entity = {}
        self._scan_contexts = {}
        self._ready_date_by_entity = {}
        self._job_min_ready_date = ""
        self._job_has_work = True
        resolver = StrategyDataResolver(self.settings)
        self._base_data_key = str(resolver.base.get("data_key") or "").strip()
        if not self._base_data_key:
            raise ValueError("settings.data.base.data_key 不能为空")
        self._min_required = resolver.min_required_records

    @classmethod
    def from_job_context(cls, job_context: JobContext) -> "EntityTaskState":
        payload = job_context.payload or {}
        loaded = job_context.init or {}
        strategy_info = payload.get("strategy_info") or {}
        settings_dict = payload.get("settings") or {}
        settings = StrategySettings.from_dict(settings_dict)
        hook_runtime, err = BaseJobExecutor.load_hooks(strategy_info, settings)
        if err is not None:
            raise RuntimeError(err.get("error") or "缺少hooks信息")

        perf = EnumJobPerfRecorder.attach(payload)
        entity_specified = list(payload.get("entity_specified") or [])
        entity_ids = [
            str(item.get("id") or "").strip()
            for item in entity_specified
            if str(item.get("id") or "").strip()
        ]
        return cls(
            entity_ids=entity_ids,
            settings=settings,
            hook_runtime=hook_runtime,
            strategy_name=str(strategy_info.get("key") or ""),
            entity_contracts=loaded.get("entity_contracts") or {},
            global_data=loaded.get("global_data") or {},
            entity_specified=entity_specified,
            payload=payload,
            perf=perf,
        )

    def begin(self, timeline: Timeline) -> None:
        if self.perf is not None:
            self.perf.begin("enumerate")
        points = timeline.points
        self._timeline_points = tuple(points)
        self._start_date = points[0] if points else timeline.start
        self._end_date = points[-1] if points else timeline.end
        calendar_dict = {
            "period_start": self._start_date,
            "period_end": self._end_date,
            "open_dates": list(points),
        }
        if self.perf is not None:
            self.perf.set_calendar_meta(
                open_dates_count=len(points),
                period_start=self._start_date,
                period_end=self._end_date,
                entities_in_job=len(self.trackers),
            )
        base_contract = self.entity_contracts.get(self._base_data_key)
        self._ready_date_by_entity = AsOfSlice.ready_date_by_entity(
            base_contract,
            list(self.trackers.keys()),
            min_required=self._min_required,
        )
        self._job_min_ready_date = AsOfSlice.job_min_ready_date(self._ready_date_by_entity)
        self._job_has_work = bool(self._job_min_ready_date)
        self._scan_contexts = {}
        for entity_item in self.entity_specified:
            entity_id = str(entity_item.get("id") or "").strip()
            if not entity_id or entity_id not in self.trackers:
                continue
            self._scan_contexts[entity_id] = StrategyContext.assemble(
                strategy_key=self.strategy_name,
                settings=self.settings,
                stock_list=[entity_id],
                entity_id=entity_id,
                entity_info={
                    "id": entity_id,
                    **self._stock_info.get(entity_id, {}),
                },
            ).with_data(
                StrategyData.build(
                    stock_list=[entity_id],
                    entity_id=entity_id,
                    entity_info={
                        "id": entity_id,
                        **self._stock_info.get(entity_id, {}),
                    },
                    calendar=calendar_dict,
                )
            )

    def on_calendar_day(self, point: str, index: int, *, is_last: bool) -> None:
        """推进时间(point) → 切数据 → 执行业务。"""
        _ = index, is_last
        now = point  # 唯一时钟：BE Timeline 传入的 point
        perf = self.perf
        entity_n = len(self.trackers)

        if (not self._job_has_work) or (
            self._job_min_ready_date and now < self._job_min_ready_date
        ):
            if perf is not None:
                perf.record_calendar_day(
                    any_bar=False,
                    bar_hits=0,
                    bar_misses=entity_n,
                    as_of_slice_sec=0.0,
                    skipped_before_ready=True,
                )
            return

        # —— 切数据 ——
        if perf is not None:
            perf.begin("enum_as_of_slice")
        sliced_by_entity = AsOfSlice.slice_contracts(
            self.entity_contracts, now, perf=perf
        )
        as_of_slice_sec = 0.0
        if perf is not None:
            as_of_slice_sec = perf.end("enum_as_of_slice", accumulate=True)

        # —— 执行业务 ——
        bar_hits = 0
        bar_misses = 0
        for entity_item in self.entity_specified:
            entity_id = str(entity_item.get("id") or "").strip()
            tracker = self.trackers.get(entity_id)
            scan_ctx = self._scan_contexts.get(entity_id)
            if tracker is None or scan_ctx is None:
                continue

            ready = self._ready_date_by_entity.get(entity_id) or ""
            if (not ready) or now < ready:
                bar_misses += 1
                continue

            per_entity = sliced_by_entity.get(entity_id, {})
            bar = AsOfSlice.base_bar(
                per_entity,
                base_data_key=self._base_data_key,
                as_of=now,
                min_required=self._min_required,
            )
            if bar is not None:
                bar_hits += 1
                self._last_bar_by_entity[entity_id] = bar
                if perf is not None:
                    perf.begin("enum_process_tick")
                tracker.process_tick(now, bar)
                if perf is not None:
                    perf.end("enum_process_tick", accumulate=True)
            else:
                bar_misses += 1

            if bar is None:
                continue

            complete_data = per_entity
            if self.global_data:
                complete_data = {**self.global_data, **per_entity}
            try:
                if perf is not None:
                    perf.begin("enum_context_fill")
                scan_ctx.refill(now=now, items=complete_data)
                if perf is not None:
                    perf.end("enum_context_fill", accumulate=True)
            except Exception as exc:
                if perf is not None:
                    perf.end("enum_context_fill", accumulate=True)
                logger.error(
                    "构建 StrategyContext 失败：entity_id=%s now=%s error=%s",
                    entity_id,
                    now,
                    exc,
                    exc_info=True,
                )
                continue

            try:
                if perf is not None:
                    perf.begin("enum_scan")
                scanned = self.hook_runtime.call("scan_opportunity", scan_ctx)
                if perf is not None:
                    perf.end("enum_scan", accumulate=True)
            except Exception as exc:
                if perf is not None:
                    perf.end("enum_scan", accumulate=True)
                logger.error(
                    "scan_opportunity 失败：entity_id=%s now=%s error=%s",
                    entity_id,
                    now,
                    exc,
                    exc_info=True,
                )
                continue

            if not isinstance(scanned, Opportunity):
                continue

            tracker.register_from_opportunity(
                scanned,
                settings=self.settings,
                open_dates=self._timeline_points,
                strategy_name=self.strategy_name,
                stock_info=self._stock_info.get(entity_id, {"id": entity_id}),
                trigger_date=now,
                trigger_price=SafeBarValue.float(bar, "close"),
                trigger_price_raw=SafeBarValue.float(bar, "close", use_raw=True),
                status_tags_provider=self.entity_contracts.get(DATA_KEY.STOCK_ST_PERIODS),
            )
            tracker.process_tick(now, bar)

        if perf is not None:
            perf.record_calendar_day(
                any_bar=bar_hits > 0,
                bar_hits=bar_hits,
                bar_misses=bar_misses,
                as_of_slice_sec=as_of_slice_sec,
            )

    def finalize(self, timeline: Timeline) -> Dict[str, Any]:
        points = timeline.points
        if points:
            last_day = points[-1]
            for entity_id, tracker in self.trackers.items():
                if not tracker.has_live:
                    continue
                last_bar = self._last_bar_by_entity.get(entity_id)
                if last_bar is None:
                    continue
                tracker.settle_incomplete(last_day, last_bar)

        if not self.payload.get("_dispatch_probe"):
            from core.modules.strategy.core.engines.enumerator.common.report_manager import (
                ReportManager,
            )

            ReportManager.worker_buffer_opportunities(
                self.payload,
                self.buffer_for_recorder(),
            )

        if self.perf is not None:
            self.perf.end("enumerate")

        opportunities_count = self.total_investment_count()
        logger.info("子进程执行完成：opportunities_count=%d", opportunities_count)
        return {
            "success": True,
            "opportunities_count": opportunities_count,
            "entities_with_opportunities": self.entities_with_investments(),
            "entities_count": len(self.entity_specified),
        }

    def total_investment_count(self) -> int:
        return sum(tracker.investment_count() for tracker in self.trackers.values())

    def entities_with_investments(self) -> int:
        return sum(1 for tracker in self.trackers.values() if tracker.investment_count())

    def buffer_for_recorder(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for entity_id, tracker in self.trackers.items():
            for inv_dict in tracker.investments_as_dicts():
                rows.append(
                    {
                        "entity_id": entity_id,
                        "date": inv_dict.get("trigger_date") or "",
                        "opportunity": inv_dict,
                    }
                )
        return rows


class EnumEntityJobExecutor(BaseJobExecutor):
    """entity_based BE 钩子 — 日历日 AsOfSlice / scan / Investment。

    边界:
    - 负责: RunCallbacks；把 EntityTaskState 写入 ``job_context.init``
    - 不负责: EnumEntityJobBuilder；BE Timeline.drive 循环（默认日历轴）
    - 调用方: EnumeratorPipeline → BacktestEngine.entity_based
    """

    task_log_label = "子进程task"

    @classmethod
    def on_before_all_tasks_start(cls, plan: Any, batches: List[Any]) -> None:
        print(
            f"  调度: {len(batches)} batches, "
            f"~{getattr(plan, 'entities_per_job', '?')} entities/job, "
            f"workers={getattr(plan, 'max_workers', '?')}",
            flush=True,
        )

    @classmethod
    def on_before_task_start(cls, job_context: Any) -> Dict[str, Any]:
        """加载 bundle，初始化 task 状态，挂到 BE ``init``。"""
        loaded = cls.load_bundle_data(job_context, log_label=cls.task_log_label)
        job_context.init = loaded
        timeline = Timeline.read_for_job(job_context.payload)
        if timeline is None:
            raise ValueError(
                "未找到引擎 timeline：EnumeratorPipeline 须传 start/end window 给 BacktestEngine"
            )
        clipped = timeline.clipped()
        state = EntityTaskState.from_job_context(job_context)
        state.begin(clipped)
        loaded[_STATE_KEY] = state
        loaded[_TIMELINE_KEY] = clipped
        return loaded

    @classmethod
    def on_tick(cls, job_context: Any, point: str, index: int) -> None:
        """BE 日历点 → AsOfSlice / scan / Investment。"""
        init = job_context.init
        if not isinstance(init, dict):
            raise TypeError("job_context.init 必须是 dict（on_before_task_start 返回值）")
        state: EntityTaskState = init[_STATE_KEY]
        timeline = init.get(_TIMELINE_KEY)
        points = getattr(timeline, "points", ()) or ()
        is_last = bool(points) and index == len(points) - 1
        state.on_calendar_day(point, index, is_last=is_last)

    @classmethod
    def on_ticks_complete(cls, job_context: Any, timeline: Any) -> Dict[str, Any]:
        """task 日历跑完 → settle + 缓冲机会。"""
        init = job_context.init
        if not isinstance(init, dict):
            raise TypeError("job_context.init 必须是 dict（on_before_task_start 返回值）")
        state: EntityTaskState = init[_STATE_KEY]
        return state.finalize(timeline)

    @classmethod
    def on_after_task_complete(cls, job_context: Any) -> None:
        if job_context.payload.get("_dispatch_probe"):
            return
        cls.flush_job_investments(job_context)


__all__ = ["ExecutorHooksContext", "EntityTaskState", "EnumEntityJobExecutor"]
