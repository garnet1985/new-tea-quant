"""entity_based 日历日业务（JobExecutor.on_tick / on_ticks_complete 驱动）。

本文件:
- EntityTimelineHooks: per-entity DataContext、Investment tick、opportunity 注册
  边界: 负责 entity 点 scan/investment 逻辑；不负责 points 迭代或 Contract 加载
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from core.modules.backtest_engine.contracts import JobContext, Timeline
from core.modules.data_contract import DATA_KEY
from core.modules.strategy.core.engines.enumerator.shared.performance_tracker.performance_tracker import (
    EnumJobPerfRecorder,
)
from core.modules.strategy.core.engines.shared.services.pit_bars import PitBars
from core.modules.strategy.core.engines.enumerator.shared.state.entity_tracker import (
    EntityTracker,
)
from core.modules.strategy.core.engines.shared.data_class import Opportunity
from core.modules.strategy.core.engines.shared.services.safe_values.safe_bar_value import SafeBarValue
from core.modules.strategy.core.engines.shared.services.entity_loader.strategy_data_resolver import (
    StrategyDataResolver,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.helpers.stock_meta import StockMetaHelper
from core.modules.strategy.core.hooks.context.data_context import DataContext

logger = logging.getLogger(__name__)


@dataclass
class EntityTimelineHooks:
    """entity 点业务：tick + scan_opportunity（无 asof）。

    边界:
    - 负责: per-entity DataContext、Investment、结果 dict
    - 不负责: points 迭代（Timeline.drive）、Contract 加载 / CSV
    - 调用方: entity JobExecutor.on_tick / on_ticks_complete
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

    trackers: Dict[str, EntityTracker] = field(init=False)
    _stock_info: Dict[str, Dict[str, Any]] = field(init=False, repr=False)
    _last_bar_by_entity: Dict[str, Dict[str, Any]] = field(init=False, repr=False)
    _scan_contexts: Dict[str, DataContext] = field(init=False, repr=False)
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
            str(entity_id).strip(): EntityTracker(entity_id=str(entity_id).strip())
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
        resolver = StrategyDataResolver(self.settings.to_dict())
        self._base_data_key = str(resolver.base.get("data_key") or "").strip()
        if not self._base_data_key:
            raise ValueError("settings.data.base.data_key 不能为空")
        self._min_required = resolver.min_required_records

    @classmethod
    def from_job_context(cls, job_context: JobContext) -> "EntityTimelineHooks":
        from core.modules.strategy.core.engines.enumerator.shared.base_executor import (
            BaseJobExecutor,
        )

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

    def on_run_begin(self, timeline: Timeline) -> None:
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
        self._ready_date_by_entity = PitBars.ready_date_by_entity(
            base_contract,
            list(self.trackers.keys()),
            min_required=self._min_required,
        )
        self._job_min_ready_date = PitBars.job_min_ready_date(self._ready_date_by_entity)
        self._job_has_work = bool(self._job_min_ready_date)
        self._scan_contexts = {}
        for entity_item in self.entity_specified:
            entity_id = str(entity_item.get("id") or "").strip()
            if not entity_id or entity_id not in self.trackers:
                continue
            ctx = DataContext.assemble(
                strategy_name=self.strategy_name,
                settings=self.settings,
                stock_list=[entity_id],
                entity_id=entity_id,
                entity_info={
                    "id": entity_id,
                    **self._stock_info.get(entity_id, {}),
                },
            )
            ctx.calendar = calendar_dict
            self._scan_contexts[entity_id] = ctx

    def on_tick(self, point: str, index: int, *, is_last: bool) -> None:
        _ = index, is_last
        now = point
        perf = self.perf
        entity_n = len(self.trackers)

        # 尽早短路：全 job 尚无任何 entity 达到 min_required → 不 until
        if (not self._job_has_work) or (
            self._job_min_ready_date and now < self._job_min_ready_date
        ):
            if perf is not None:
                perf.record_calendar_day(
                    any_bar=False,
                    bar_hits=0,
                    bar_misses=entity_n,
                    pit_sec=0.0,
                    skipped_before_ready=True,
                )
            return

        if perf is not None:
            perf.begin("enum_pit_until")
        pit_data_by_entity = PitBars.load_pit_by_entity(
            self.entity_contracts, now, perf=perf
        )
        pit_sec = 0.0
        if perf is not None:
            pit_sec = perf.end("enum_pit_until", accumulate=True)

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

            per_entity_pit = pit_data_by_entity.get(entity_id, {})
            bar = PitBars.bar_on(
                per_entity_pit,
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

            complete_data = per_entity_pit
            if self.global_data:
                complete_data = {**self.global_data, **per_entity_pit}
            try:
                if perf is not None:
                    perf.begin("enum_context_fill")
                scan_ctx.refill(now=now, data=complete_data)
                if perf is not None:
                    perf.end("enum_context_fill", accumulate=True)
            except Exception as exc:
                if perf is not None:
                    perf.end("enum_context_fill", accumulate=True)
                logger.error(
                    "构建 DataContext 失败：entity_id=%s now=%s error=%s",
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
                trigger_price=float(bar["close"]),
                trigger_price_raw=SafeBarValue.float(bar, "close", use_raw=True),
                status_tags_provider=self.entity_contracts.get(DATA_KEY.STOCK_ST_PERIODS),
            )
            tracker.process_tick(now, bar)

        if perf is not None:
            perf.record_calendar_day(
                any_bar=bar_hits > 0,
                bar_hits=bar_hits,
                bar_misses=bar_misses,
                pit_sec=pit_sec,
            )

    def on_run_end(self, timeline: Timeline) -> Dict[str, Any]:
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
            from core.modules.strategy.core.engines.enumerator.shared.report_manager import (
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


__all__ = ["EntityTimelineHooks"]
