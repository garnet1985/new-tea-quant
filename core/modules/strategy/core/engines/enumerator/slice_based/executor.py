"""slice_based JobExecutor — BE RunCallbacks；日业务与 per-task 状态。

本文件（slice 两件套之一，与 JobBuilder；见 ``BOUNDARY_NOTES.md``「与 BE 的关系」）:
- JobExecutor: on_before_task_start / on_tick / on_ticks_complete / flush
- SliceTaskState: 挂在 ``job_context.init`` 的可变袋（**不是**第二套 BE session）

边界:
- 负责: 经 callback 改写执行中的数据与逻辑（asof / Investment）
- 不负责: 建 jobs；覆盖 BE 默认日历轴；平行 session / TimelineBuilder
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from core.modules.backtest_engine.contracts import JobContext, Timeline
from core.modules.data_contract import DATA_KEY
from core.modules.strategy.contracts import CalendarAsOfResult, Opportunity
from core.modules.strategy.core.engines.enumerator.common.base_executor import (
    BaseJobExecutor,
    ExecutorHooksContext,
)
from core.modules.strategy.core.engines.enumerator.common.performance_tracker.performance_tracker import (
    EnumJobPerfRecorder,
)
from core.modules.strategy.core.engines.shared.services.pit_bars import PitBars
from core.modules.strategy.core.engines.enumerator.common.state.investment_tracker import (
    InvestmentTracker,
)
from core.modules.strategy.core.engines.shared.services.safe_values.safe_bar_value import SafeBarValue
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
class SliceTaskState:
    """单 task 可变状态，存于 ``job_context.init``（BE hold 的 init）。

    不是平行于 BE 的 session；仅是 Executor 在 init 袋里放的 trackers / asof 状态。
    """

    entity_ids: List[str]
    settings: StrategySettings
    hook_runtime: Any
    strategy_name: str
    entity_contracts: Dict[str, Any]
    global_data: Dict[str, Any]
    payload: Dict[str, Any]
    perf: Optional[EnumJobPerfRecorder] = None

    trackers: Dict[str, InvestmentTracker] = field(init=False)
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
    _ready_date_by_entity: Dict[str, str] = field(
        default_factory=dict, init=False, repr=False
    )
    _job_min_ready_date: str = field(default="", init=False, repr=False)
    _job_has_work: bool = field(default=True, init=False, repr=False)

    def __post_init__(self) -> None:
        ids = [str(eid).strip() for eid in self.entity_ids if str(eid).strip()]
        self.entity_ids = ids
        self.trackers = {eid: InvestmentTracker(entity_id=eid) for eid in ids}
        self._stock_info = {eid: StockMetaHelper.load(eid) for eid in ids}
        self._ready_date_by_entity = {}
        self._job_min_ready_date = ""
        self._job_has_work = True
        self._assert_entry_price_model(self.settings)
        self._rebalance_period = self._resolve_rebalance_period(self.settings)
        resolver = StrategyDataResolver(self.settings)
        self._base_data_key = str(resolver.base.get("data_key") or "").strip()
        if not self._base_data_key:
            raise ValueError("settings.data.base.data_key 不能为空")
        self._min_required = resolver.min_required_records

    @classmethod
    def from_job_context(cls, job_context: JobContext) -> "SliceTaskState":
        payload = job_context.payload or {}
        loaded = job_context.init or {}
        strategy_info = payload.get("strategy_info") or {}
        settings = StrategySettings.from_dict(payload.get("settings") or {})
        hook_runtime, err = BaseJobExecutor.load_hooks(strategy_info, settings)
        if err is not None:
            raise RuntimeError(err.get("error") or "缺少hooks信息")

        entity_ids = cls._resolve_entity_ids(payload)
        return cls(
            entity_ids=entity_ids,
            settings=settings,
            hook_runtime=hook_runtime,
            strategy_name=str(strategy_info.get("key") or ""),
            entity_contracts=loaded.get("entity_contracts") or {},
            global_data=loaded.get("global_data") or {},
            payload=payload,
            perf=EnumJobPerfRecorder.attach(payload),
        )

    @staticmethod
    def _resolve_entity_ids(payload: Dict[str, Any]) -> List[str]:
        raw = payload.get("entity_ids")
        if not isinstance(raw, list) or not raw:
            raise ValueError("slice_based payload requires non-empty entity_ids")
        ids = [str(item).strip() for item in raw if str(item).strip()]
        if not ids:
            raise ValueError("slice_based payload entity_ids 不能为空")
        return ids

    def begin(self, timeline: Timeline) -> None:
        if self.perf is not None:
            self.perf.begin("enumerate")
        self._open_dates = list(timeline.points)
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
        base_contract = self.entity_contracts.get(self._base_data_key)
        self._ready_date_by_entity = PitBars.ready_date_by_entity(
            base_contract,
            list(self.trackers.keys()),
            min_required=self._min_required,
        )
        self._job_min_ready_date = PitBars.job_min_ready_date(self._ready_date_by_entity)
        self._job_has_work = bool(self._job_min_ready_date)

    def on_calendar_day(self, point: str, index: int, *, is_last: bool) -> None:
        as_of = point
        perf = self.perf

        # 尽早短路：全 job 尚无任何 entity 达到 min_required → 不 until / 不 asof
        if (not self._job_has_work) or (
            self._job_min_ready_date and as_of < self._job_min_ready_date
        ):
            if perf is not None:
                perf.record_calendar_day(
                    any_bar=False,
                    bar_hits=0,
                    bar_misses=len(self.trackers),
                    pit_sec=0.0,
                    skipped_before_ready=True,
                )
            # 空点前缀不计入 slice window
            self._window_start_idx = index + 1
            self._window_t0 = time.perf_counter()
            return

        if perf is not None:
            perf.begin("enum_pit_until")
        pit_by_entity = PitBars.load_pit_by_entity(
            self.entity_contracts, as_of, perf=perf
        )
        if perf is not None:
            perf.end("enum_pit_until", accumulate=True)

        for entity_id, tracker in self.trackers.items():
            ready = self._ready_date_by_entity.get(entity_id) or ""
            if (not ready) or as_of < ready:
                continue
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
            tracker.process_tick(as_of, bar)
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
            asof_result = self.hook_runtime.call("on_calendar_asof", asof_ctx)
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
                if not tracker.has_live:
                    continue
                bar = self._last_bar_by_entity.get(entity_id)
                if bar is None:
                    continue
                tracker.settle_incomplete(as_of, bar)

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
        tracker: InvestmentTracker,
        entity_id: str,
        as_of: str,
        pit_by_entity: Dict[str, Dict[str, Any]],
        calendar: Dict[str, Any],
        open_dates: Sequence[str],
    ) -> None:
        if tracker.has_live:
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
            self.hook_runtime.call_if_overridden("on_before_scan", scan_ctx)
            opportunity = self.hook_runtime.call("scan_opportunity", scan_ctx)
            self.hook_runtime.call_if_overridden(
                "on_after_scan",
                DataContext.fill(
                    self._ctx_base,
                    now=as_of,
                    data=complete_data,
                    calendar=calendar,
                    entity_id=entity_id,
                    entity_info={"id": entity_id, **stock_info},
                    opportunity=opportunity if isinstance(opportunity, Opportunity) else None,
                ),
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
            trigger_price_raw=SafeBarValue.float(bar, "close", use_raw=True),
            status_tags_provider=self.entity_contracts.get(DATA_KEY.STOCK_ST_PERIODS),
        )
        tracker.process_tick(as_of, bar)

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
    def _resolve_rebalance_period(settings: StrategySettings) -> str:
        core = settings.raw_settings.get("core")
        if not isinstance(core, dict):
            return "year"
        period = str(core.get("rebalance_period") or "year").strip().lower()
        return period if period in {"month", "year"} else "year"

    @staticmethod
    def _assert_entry_price_model(settings: StrategySettings) -> None:
        model = str(settings.simulation.enter_price or "").strip().lower()
        if model and model != "close":
            raise ValueError(
                f"slice_based 当前仅支持 simulation.assumption.tradability.enter_price"
                f"='close'，实际: {model!r}"
            )


_STATE_KEY = "_slice_task_state"
_TIMELINE_KEY = "_slice_timeline"


class JobExecutor(BaseJobExecutor):
    """slice_based BE 钩子 — 日历日 asof / Investment。

    边界:
    - 负责: RunCallbacks；把 SliceTaskState 写入 ``job_context.init``
    - 不负责: JobBuilder；BE Timeline.drive 循环（默认日历轴）
    - 调用方: EnumeratorPipeline → BacktestEngine.slice_based
    """

    task_log_label = "slice task"

    @classmethod
    def on_before_all_tasks_start(cls, plan: Any, batches: List[Any]) -> None:
        print(
            f"  调度: {len(batches)} batches, "
            f"slice_open_days={getattr(plan, 'slice_open_days', '?')}, "
            f"reader_workers={getattr(plan, 'reader_workers', '?')}",
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
        state = SliceTaskState.from_job_context(job_context)
        state.begin(clipped)
        loaded[_STATE_KEY] = state
        loaded[_TIMELINE_KEY] = clipped
        return loaded

    @classmethod
    def on_tick(cls, job_context: Any, point: str, index: int) -> None:
        """BE 日历点 → asof / Investment。"""
        init = job_context.init
        if not isinstance(init, dict):
            raise TypeError("job_context.init 必须是 dict（on_before_task_start 返回值）")
        state: SliceTaskState = init[_STATE_KEY]
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
        state: SliceTaskState = init[_STATE_KEY]
        return state.finalize(timeline)


__all__ = ["ExecutorHooksContext", "SliceTaskState", "JobExecutor"]
