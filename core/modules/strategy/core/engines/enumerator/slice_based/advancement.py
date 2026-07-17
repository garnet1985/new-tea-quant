"""slice_based AdvancementHooks：BE CalendarAdvancer 驱动，本类实现 asof 日业务。"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from core.modules.backtest_engine.contracts import JobContext
from core.modules.strategy.contracts import CalendarAsOfResult, Opportunity
from core.modules.strategy.core.engines.enumerator.shared.services.enum_job_perf import (
    EnumJobPerfRecorder,
)
from core.modules.strategy.core.engines.enumerator.shared.services.pit_bars import PitBars
from core.modules.strategy.core.engines.enumerator.shared.state.entity_tracker import (
    EntityTracker,
)
from core.modules.strategy.core.engines.shared.data_class import InvestmentTickInput
from core.modules.strategy.core.engines.shared.services.entity_loader.strategy_data_resolver import (
    StrategyDataResolver,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.helpers.calendar import CalendarOpenDateHelper
from core.modules.strategy.core.helpers.stock_meta import StockMetaHelper
from core.modules.strategy.core.hooks.context.data_context import DataContext

logger = logging.getLogger(__name__)


@dataclass
class SliceAdvancementHooks:
    """slice 日业务：tick-all → on_calendar_asof → scan 选股。

    边界:
    - 负责: asof 选股、Investment、force_exit、head RSS 采样、结果 dict
    - 不负责: open_dates 迭代（CalendarAdvancer）、Contract 加载 / CSV
    - 调用方: BacktestEngine via build_slice_advancement_hooks
    """

    entity_ids: List[str]
    settings: StrategySettings
    hooks: Any
    strategy_name: str
    entity_contracts: Dict[str, Any]
    global_data: Dict[str, Any]
    payload: Dict[str, Any]
    perf: Optional[EnumJobPerfRecorder] = None

    trackers: Dict[str, EntityTracker] = field(init=False)
    _stock_info: Dict[str, Dict[str, Any]] = field(init=False, repr=False)
    _session_state: Dict[str, Any] = field(default_factory=dict, init=False, repr=False)
    _open_dates: List[str] = field(default_factory=list, init=False, repr=False)
    _last_bar_by_entity: Dict[str, Dict[str, Any]] = field(
        default_factory=dict, init=False, repr=False
    )
    _base_data_key: str = field(init=False, repr=False)
    _min_required: int = field(init=False, repr=False)
    _rebalance_period: str = field(init=False, repr=False)
    _ctx_base: Any = field(init=False, repr=False)
    _slice_open_days: int = field(default=20, init=False, repr=False)
    _head_sample_slices: int = field(default=0, init=False, repr=False)
    _slice_samples: List[Dict[str, Any]] = field(default_factory=list, init=False, repr=False)
    _baseline_rss_mb: float = field(default=0.0, init=False, repr=False)
    _window_start_idx: int = field(default=0, init=False, repr=False)
    _slice_index: int = field(default=0, init=False, repr=False)
    _window_t0: float = field(default=0.0, init=False, repr=False)

    def __post_init__(self) -> None:
        ids = [str(eid).strip() for eid in self.entity_ids if str(eid).strip()]
        self.entity_ids = ids
        self.trackers = {eid: EntityTracker(entity_id=eid) for eid in ids}
        self._stock_info = {eid: StockMetaHelper.load(eid) for eid in ids}
        settings_dict = self.settings.to_dict()
        self._assert_entry_price_model(settings_dict)
        self._rebalance_period = self._resolve_rebalance_period(settings_dict)
        resolver = StrategyDataResolver(settings_dict)
        self._base_data_key = str(resolver.base.get("data_key") or "").strip()
        if not self._base_data_key:
            raise ValueError("settings.data.base.data_key 不能为空")
        self._min_required = resolver.min_required_records

    @classmethod
    def from_job_context(cls, job_context: JobContext) -> "SliceAdvancementHooks":
        from core.modules.strategy.core.engines.enumerator.shared.executor_hooks import (
            ExecutorHooks,
        )

        payload = job_context.payload or {}
        loaded = job_context.init or {}
        strategy_info = payload.get("strategy_info") or {}
        settings = StrategySettings.from_dict(payload.get("settings") or {})
        hooks_instance, err = ExecutorHooks.load_hooks(strategy_info)
        if err is not None:
            raise RuntimeError(err.get("error") or "缺少hooks信息")

        entity_ids = cls._resolve_entity_ids(payload)
        return cls(
            entity_ids=entity_ids,
            settings=settings,
            hooks=hooks_instance,
            strategy_name=str(strategy_info.get("key") or ""),
            entity_contracts=loaded.get("entity_contracts") or {},
            global_data=loaded.get("global_data") or {},
            payload=payload,
            perf=EnumJobPerfRecorder.attach(payload),
        )

    @staticmethod
    def _resolve_entity_ids(payload: Dict[str, Any]) -> List[str]:
        for key in ("entity_ids", "stock_ids"):
            raw = payload.get(key)
            if isinstance(raw, list) and raw:
                return [str(item).strip() for item in raw if str(item).strip()]
        specified = payload.get("entity_specified") or []
        return [
            str(item.get("id") or "").strip()
            for item in specified
            if isinstance(item, dict) and str(item.get("id") or "").strip()
        ]

    def resolve_open_dates(self, job_context: JobContext) -> List[str]:
        payload = job_context.payload or {}
        raw = payload.get("open_dates")
        if isinstance(raw, list) and raw:
            return [str(day).strip() for day in raw if str(day).strip()]

        calendar = payload.get("backtest_calendar")
        if isinstance(calendar, dict):
            cal_dates = calendar.get("open_dates")
            if isinstance(cal_dates, list) and cal_dates:
                return [str(day).strip() for day in cal_dates if str(day).strip()]

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
        open_dates = self.resolve_open_dates(job_context)
        start = str(payload.get("start_date") or (open_dates[0] if open_dates else "")).strip()
        end = str(payload.get("end_date") or (open_dates[-1] if open_dates else "")).strip()
        return start, end

    def on_run_begin(self, open_dates: Sequence[str]) -> None:
        if self.perf is not None:
            self.perf.begin("enumerate")
        self._open_dates = list(open_dates)
        self._slice_open_days = max(
            1,
            int(
                self.payload.get("_slice_open_days")
                or (self.payload.get("_slice_plan") or {}).get("slice_open_days")
                or 20
            ),
        )
        self._head_sample_slices = max(
            0, int(self.payload.get("_slice_head_sample_slices") or 0)
        )
        self._slice_samples = []
        self._baseline_rss_mb = self._process_rss_mb()
        self._ctx_base = DataContext.assemble(
            strategy_name=self.strategy_name,
            settings=self.settings,
            stock_list=list(self.entity_ids),
        )
        self._window_start_idx = 0
        self._slice_index = 0
        self._window_t0 = time.perf_counter()

    def on_day(self, day: str, index: int, *, is_last: bool) -> None:
        as_of = day
        perf = self.perf
        if perf is not None:
            perf.begin("enum_pit_until")
        pit_by_entity = PitBars.load_pit_by_entity(
            self.entity_contracts, as_of, perf=perf
        )
        if perf is not None:
            perf.end("enum_pit_until", accumulate=True)

        for entity_id, tracker in self.trackers.items():
            bar = PitBars.bar_on(
                pit_by_entity.get(entity_id, {}),
                base_data_key=self._base_data_key,
                as_of=as_of,
                min_required=self._min_required,
            )
            if bar is None:
                continue
            self._last_bar_by_entity[entity_id] = bar
            if perf is not None:
                perf.begin("enum_process_tick")
            tracker.process_tick(
                InvestmentTickInput(as_of_date=as_of, bar=bar, data_as_of=as_of)
            )
            if perf is not None:
                perf.end("enum_process_tick", accumulate=True)

        stocks_ctx = self._build_stocks_context(
            pit_by_entity,
            as_of=as_of,
        )
        calendar = self._build_calendar_view(
            as_of,
            stocks=stocks_ctx,
            open_date_index=index,
        )

        asof_ctx = DataContext.fill(self._ctx_base, now=as_of, calendar=calendar)
        try:
            if perf is not None:
                perf.begin("enum_calendar_asof")
            asof_result = self.hooks.on_calendar_asof(asof_ctx)
            if perf is not None:
                perf.end("enum_calendar_asof", accumulate=True)
        except Exception as exc:
            if perf is not None:
                perf.end("enum_calendar_asof", accumulate=True)
            logger.error(
                "on_calendar_asof 失败：as_of=%s error=%s",
                as_of,
                exc,
                exc_info=True,
            )
            return

        if not isinstance(asof_result, CalendarAsOfResult):
            raise TypeError(
                f"on_calendar_asof 必须返回 CalendarAsOfResult，实际: {type(asof_result).__name__}"
            )
        self._session_state = dict(asof_result.session_state)
        calendar["session_state"] = dict(self._session_state)

        force_exit_date = str(self._session_state.get("force_exit_open_date") or "").strip()
        if force_exit_date == as_of:
            for entity_id, tracker in self.trackers.items():
                if not tracker.active:
                    continue
                bar = self._last_bar_by_entity.get(entity_id)
                if bar is None:
                    continue
                tracker.settle_incomplete(
                    InvestmentTickInput(as_of_date=as_of, bar=bar, data_as_of=as_of)
                )

        open_dates_tuple = tuple(self._open_dates)
        for stock_id in asof_result.stocks:
            entity_id = str(stock_id).strip()
            tracker = self.trackers.get(entity_id)
            if tracker is None:
                raise ValueError(f"on_calendar_asof 返回未知 stock_id: {entity_id}")
            self._scan_entity(
                tracker=tracker,
                entity_id=entity_id,
                as_of=as_of,
                pit_by_entity=pit_by_entity,
                calendar=calendar,
                open_dates=open_dates_tuple,
            )

        days_in_window = index - self._window_start_idx + 1
        hit_window_end = days_in_window >= self._slice_open_days
        if (
            self._head_sample_slices > 0
            and self._slice_index < self._head_sample_slices
            and (hit_window_end or is_last)
        ):
            elapsed = max(0.0, time.perf_counter() - self._window_t0)
            rss = self._process_rss_mb()
            half = round(elapsed / 2.0, 4)
            self._slice_samples.append(
                {
                    "slice_index": self._slice_index,
                    "load_sec": half,
                    "compute_sec": half,
                    "serialize_sec": 0.0,
                    "deserialize_sec": 0.0,
                    "rss_after_mb": round(rss, 1),
                    "payload_mb": round(max(0.0, rss - self._baseline_rss_mb), 1),
                    "payload_bytes": int(
                        max(0.0, rss - self._baseline_rss_mb) * 1024 * 1024
                    ),
                }
            )
            self._slice_index += 1
            self._window_start_idx = index + 1
            self._window_t0 = time.perf_counter()

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
        logger.info("slice 执行完成：opportunities_count=%d", opportunities_count)
        return {
            "success": True,
            "opportunities_count": opportunities_count,
            "entities_with_opportunities": self.entities_with_investments(),
            "entities_count": len(self.entity_ids),
            "performance_metrics": {
                "calendar_slice_runtime_plan": self.slice_runtime_plan_dict(),
            },
        }

    def _scan_entity(
        self,
        *,
        tracker: EntityTracker,
        entity_id: str,
        as_of: str,
        pit_by_entity: Dict[str, Dict[str, Any]],
        calendar: Dict[str, Any],
        open_dates: Sequence[str],
    ) -> None:
        if tracker.active:
            return

        per_entity_pit = pit_by_entity.get(entity_id, {})
        bar = PitBars.bar_on(
            per_entity_pit,
            base_data_key=self._base_data_key,
            as_of=as_of,
            min_required=self._min_required,
        )
        if bar is None:
            return

        complete_data = dict(per_entity_pit)
        if self.global_data:
            complete_data = {**self.global_data, **per_entity_pit}

        stock_info = self._stock_info.get(entity_id, {"id": entity_id})
        scan_ctx = DataContext.fill(
            self._ctx_base,
            now=as_of,
            data=complete_data,
            calendar=calendar,
            entity_id=entity_id,
            entity_info={"id": entity_id, **stock_info},
        )

        perf = self.perf
        try:
            if perf is not None:
                perf.begin("enum_scan")
            self.hooks.on_before_scan(scan_ctx)
            opportunity = self.hooks.scan_opportunity(scan_ctx)
            self.hooks.on_after_scan(
                DataContext.fill(
                    self._ctx_base,
                    now=as_of,
                    data=complete_data,
                    calendar=calendar,
                    entity_id=entity_id,
                    entity_info={"id": entity_id, **stock_info},
                    opportunity=opportunity if isinstance(opportunity, Opportunity) else None,
                )
            )
            if perf is not None:
                perf.end("enum_scan", accumulate=True)
        except Exception as exc:
            if perf is not None:
                perf.end("enum_scan", accumulate=True)
            logger.error(
                "scan 失败：entity_id=%s as_of=%s error=%s",
                entity_id,
                as_of,
                exc,
                exc_info=True,
            )
            return

        if not isinstance(opportunity, Opportunity):
            return

        tracker.register_from_opportunity(
            opportunity,
            settings=self.settings,
            open_dates=open_dates,
            strategy_name=self.strategy_name,
            stock_info=stock_info,
            trigger_date=as_of,
            trigger_price=float(bar["close"]),
        )
        tracker.process_tick(
            InvestmentTickInput(as_of_date=as_of, bar=bar, data_as_of=as_of)
        )

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

    def slice_runtime_plan_dict(self) -> Dict[str, Any]:
        return {
            "baseline_rss_mb": float(self._baseline_rss_mb or 0.0),
            "slice_samples": list(self._slice_samples),
        }

    @staticmethod
    def _process_rss_mb() -> float:
        try:
            import os

            import psutil

            return float(psutil.Process(os.getpid()).memory_info().rss) / (1024.0 * 1024.0)
        except Exception:
            return 0.0

    def _build_stocks_context(
        self,
        pit_by_entity: Dict[str, Dict[str, Any]],
        *,
        as_of: str,
    ) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        for entity_id in self.entity_ids:
            per_entity = pit_by_entity.get(entity_id, {})
            if (
                PitBars.bar_on(
                    per_entity,
                    base_data_key=self._base_data_key,
                    as_of=as_of,
                    min_required=self._min_required,
                )
                is None
            ):
                continue
            if self.global_data:
                packed = {**self.global_data, **per_entity}
            else:
                packed = dict(per_entity)
            base_rows = packed.get(self._base_data_key)
            if isinstance(base_rows, list) and "klines" not in packed:
                packed["klines"] = base_rows
            out[entity_id] = packed
        return out

    def _build_calendar_view(
        self,
        as_of: str,
        *,
        stocks: Dict[str, Dict[str, Any]],
        open_date_index: int,
    ) -> Dict[str, Any]:
        all_open: Sequence[str] = self._open_dates
        if self._rebalance_period == "month":
            is_period_start = CalendarOpenDateHelper.is_first_open_of_month(as_of, all_open)
            is_period_end = CalendarOpenDateHelper.is_last_open_of_month(as_of, all_open)
        else:
            is_period_start = CalendarOpenDateHelper.is_first_open_of_year(as_of, all_open)
            is_period_end = CalendarOpenDateHelper.is_last_open_of_year(as_of, all_open)
        return {
            "as_of_date": as_of,
            "session_state": dict(self._session_state),
            "stocks": dict(stocks),
            "open_date_index": open_date_index,
            "is_period_start": is_period_start,
            "is_period_end": is_period_end,
            "is_first_open_of_month": CalendarOpenDateHelper.is_first_open_of_month(
                as_of, all_open
            ),
            "is_last_open_of_month": CalendarOpenDateHelper.is_last_open_of_month(
                as_of, all_open
            ),
            "is_first_open_of_year": CalendarOpenDateHelper.is_first_open_of_year(
                as_of, all_open
            ),
            "is_last_open_of_year": CalendarOpenDateHelper.is_last_open_of_year(
                as_of, all_open
            ),
        }

    @staticmethod
    def _resolve_rebalance_period(settings: Dict[str, Any]) -> str:
        core = settings.get("core")
        if not isinstance(core, dict):
            return "year"
        period = str(core.get("rebalance_period") or "year").strip().lower()
        return period if period in {"month", "year"} else "year"

    @staticmethod
    def _assert_entry_price_model(settings: Dict[str, Any]) -> None:
        simulation = settings.get("simulation")
        if not isinstance(simulation, dict):
            return
        model = simulation.get("buy_price_model")
        if model is None:
            return
        if model != "close":
            raise ValueError(
                f"slice_based 当前仅支持 simulation.buy_price_model='close'，实际: {model!r}"
            )


def build_slice_advancement_hooks(job_context: JobContext) -> SliceAdvancementHooks:
    """可 pickle 的 factory（模块级函数）。"""
    return SliceAdvancementHooks.from_job_context(job_context)


__all__ = ["SliceAdvancementHooks", "build_slice_advancement_hooks"]
