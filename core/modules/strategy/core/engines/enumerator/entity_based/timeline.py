"""entity_based TimelineHooks：BE TimelineDriver 驱动，本类实现单日业务。"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from core.modules.backtest_engine.contracts import JobContext
from core.modules.strategy.core.engines.enumerator.shared.performance_tracker.performance_tracker import (
    EnumJobPerfRecorder,
)
from core.modules.strategy.core.engines.enumerator.shared.services.pit_bars import PitBars
from core.modules.strategy.core.engines.enumerator.shared.state.entity_tracker import (
    EntityTracker,
)
from core.modules.strategy.core.engines.shared.data_class import InvestmentTickInput, Opportunity
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
    """entity 日业务：tick + scan_opportunity（无 asof）。

    边界:
    - 负责: per-entity DataContext、Investment 生命周期、结果 dict
    - 不负责: open_dates 迭代（TimelineDriver）、Contract 加载 / CSV
    - 调用方: BacktestEngine via EntityTimelineHooks.factory
    """

    entity_ids: List[str]
    settings: StrategySettings
    hooks: Any
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
    _open_dates_tuple: tuple = field(default_factory=tuple, init=False, repr=False)
    _start_date: str = field(default="", init=False, repr=False)
    _end_date: str = field(default="", init=False, repr=False)

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
        hooks_instance, err = BaseJobExecutor.load_hooks(strategy_info)
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
            hooks=hooks_instance,
            strategy_name=str(strategy_info.get("key") or ""),
            entity_contracts=loaded.get("entity_contracts") or {},
            global_data=loaded.get("global_data") or {},
            entity_specified=entity_specified,
            payload=payload,
            perf=perf,
        )

    def resolve_open_dates(self, job_context: JobContext) -> List[str]:
        from core.modules.data_contract import DATA_KEY

        loaded = job_context.init or {}
        global_data = loaded.get("global_data") or {}
        calendar_data = global_data.get(DATA_KEY.TRADE_CALENDAR, [])
        return [
            str(item.get("date") or "").strip()
            for item in calendar_data
            if item.get("is_open") and str(item.get("date") or "").strip()
        ]

    def resolve_period(self, job_context: JobContext) -> tuple:
        payload = job_context.payload or {}
        entity_shared = payload.get("entity_shared") or {}
        first = list(entity_shared.values())[0] if entity_shared else {}
        open_dates = self.resolve_open_dates(job_context)
        start = str((first or {}).get("start") or (open_dates[0] if open_dates else "")).strip()
        end = str((first or {}).get("end") or (open_dates[-1] if open_dates else "")).strip()
        return start, end

    def on_run_begin(self, open_dates: Sequence[str]) -> None:
        if self.perf is not None:
            self.perf.begin("enumerate")
        self._open_dates_tuple = tuple(open_dates)
        self._start_date = open_dates[0] if open_dates else ""
        self._end_date = open_dates[-1] if open_dates else ""
        calendar_dict = {
            "period_start": self._start_date,
            "period_end": self._end_date,
            "open_dates": list(open_dates),
        }
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

    def on_day(self, day: str, index: int, *, is_last: bool) -> None:
        _ = index, is_last
        now = day
        perf = self.perf
        if perf is not None:
            perf.begin("enum_pit_until")
        pit_data_by_entity = PitBars.load_pit_by_entity(
            self.entity_contracts, now, perf=perf
        )
        if perf is not None:
            perf.end("enum_pit_until", accumulate=True)

        for entity_item in self.entity_specified:
            entity_id = str(entity_item.get("id") or "").strip()
            tracker = self.trackers.get(entity_id)
            scan_ctx = self._scan_contexts.get(entity_id)
            if tracker is None or scan_ctx is None:
                continue

            per_entity_pit = pit_data_by_entity.get(entity_id, {})
            bar = PitBars.bar_on(
                per_entity_pit,
                base_data_key=self._base_data_key,
                as_of=now,
                min_required=self._min_required,
            )
            if bar is not None:
                self._last_bar_by_entity[entity_id] = bar
                tick = InvestmentTickInput(as_of_date=now, bar=bar, data_as_of=now)
                if perf is not None:
                    perf.begin("enum_process_tick")
                tracker.process_tick(tick)
                if perf is not None:
                    perf.end("enum_process_tick", accumulate=True)

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
                scanned = self.hooks.scan_opportunity(scan_ctx)
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
                open_dates=self._open_dates_tuple,
                strategy_name=self.strategy_name,
                stock_info=self._stock_info.get(entity_id, {"id": entity_id}),
                trigger_date=now,
                trigger_price=float(bar["close"]),
            )
            tracker.process_tick(
                InvestmentTickInput(as_of_date=now, bar=bar, data_as_of=now)
            )

    def on_run_end(self, open_dates: Sequence[str]) -> Dict[str, Any]:
        if open_dates:
            last_day = open_dates[-1]
            for entity_id, tracker in self.trackers.items():
                if not tracker.active:
                    continue
                last_bar = self._last_bar_by_entity.get(entity_id)
                if last_bar is None:
                    continue
                tracker.settle_incomplete(
                    InvestmentTickInput(
                        as_of_date=last_day, bar=last_bar, data_as_of=last_day
                    )
                )

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

        opportunities_count = self.total_recorded_count()
        logger.info("子进程执行完成：opportunities_count=%d", opportunities_count)
        return {
            "success": True,
            "opportunities_count": opportunities_count,
            "entities_with_opportunities": self.entities_with_investments(),
            "entities_count": len(self.entity_specified),
        }

    def total_recorded_count(self) -> int:
        return sum(len(tracker.recorded) for tracker in self.trackers.values())

    def entities_with_investments(self) -> int:
        return sum(1 for tracker in self.trackers.values() if tracker.recorded)

    def buffer_for_recorder(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for entity_id, tracker in self.trackers.items():
            for inv_dict in tracker.recorded_as_dicts():
                rows.append(
                    {
                        "entity_id": entity_id,
                        "date": inv_dict.get("trigger_date") or "",
                        "opportunity": inv_dict,
                    }
                )
        return rows

    @staticmethod
    def factory(job_context: JobContext) -> "EntityTimelineHooks":
        """可 pickle 的 TimelineHooksFactory。"""
        return EntityTimelineHooks.from_job_context(job_context)


__all__ = ["EntityTimelineHooks"]
