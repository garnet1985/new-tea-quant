"""slice_based EnumSliceJobExecutor — BE RunCallbacks；日业务与 per-task 状态。

本文件（slice 两件套之一，与 EnumSliceJobBuilder；见 ``docs/notes/BOUNDARY_NOTES.md``「与 BE 的关系」）:
- EnumSliceJobExecutor: on_task_start / on_tick / on_task_complete / flush
- SliceTaskState: 挂在 ``job_context.init`` 的可变袋（**不是**第二套 BE session）

边界:
- 负责: 经 callback 改写执行中的数据与逻辑（asof / Investment）
- 不负责: 建 jobs；覆盖 BE 默认日历轴；片窗装载 / reader / queue / 进度
  （上述由 BE ``SliceOrchestrator`` 驱动，Strategy 只消费 ``init["entity_contracts"]``）
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from core.modules.backtest_engine.contracts import JobContext, Timeline
from core.modules.data_contract.contracts import DATA_KEY
from core.modules.strategy.contracts import CalendarAsOfResult, Opportunity
from core.modules.strategy.core.engines.enumerator.common.base_executor import (
    BaseJobExecutor,
    ExecutorHooksContext,
)
from core.modules.strategy.core.engines.enumerator.common.performance_tracker.performance_tracker import (
    EnumJobPerfRecorder,
)
from core.modules.strategy.core.engines.shared.services.as_of_slice import AsOfSlice
from core.modules.strategy.core.engines.enumerator.common.state.investment_tracker import (
    InvestmentTracker,
)
from core.modules.strategy.core.engines.shared.data_class.investment import ExitReason
from core.modules.strategy.core.engines.shared.services.safe_values.safe_bar_value import SafeBarValue
from core.modules.strategy.core.services.entity_loader.strategy_data_resolver import (
    StrategyDataResolver,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.helpers.calendar import CalendarOpenDateHelper
from core.modules.strategy.core.helpers.stock_meta import StockMetaHelper
from core.modules.strategy.core.hooks.hook_params import StrategyContext

logger = logging.getLogger(__name__)


@dataclass
class SliceTaskState:
    """单 task 可变业务状态，存于 ``job_context.init``（BE hold 的 init）。

    不是平行于 BE 的 session；仅是 Executor 在 init 袋里放的 trackers / asof 状态。
    调度（窗宽 / reader / queue / 进度）由 BE ``SliceOrchestrator`` 持有，本类不感知。
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
    _ready_date_by_entity: Dict[str, str] = field(
        default_factory=dict, init=False, repr=False
    )
    _job_min_ready_date: str = field(default="", init=False, repr=False)
    _job_has_work: bool = field(default=True, init=False, repr=False)
    _contracts_token: int = field(default=0, init=False, repr=False)

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
        self._ctx_base = StrategyContext.assemble(
            strategy_key=self.strategy_name,
            settings=self.settings,
            stock_list=list(self.entity_ids),
        )
        self.entity_contracts = {}
        self._contracts_token = 0
        if not self._open_dates:
            self._ready_date_by_entity = {}
            self._job_min_ready_date = ""
            self._job_has_work = False

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
        self.entity_contracts = entity_contracts if isinstance(entity_contracts, dict) else {}
        self._contracts_token = token
        if global_data is not None and isinstance(global_data, dict):
            self.global_data = global_data
        if self.entity_contracts:
            self._refresh_ready_dates()
        else:
            self._ready_date_by_entity = {}
            self._job_min_ready_date = ""
            self._job_has_work = False

    def _refresh_ready_dates(self) -> None:
        base_contract = self.entity_contracts.get(self._base_data_key)
        self._ready_date_by_entity = AsOfSlice.ready_date_by_entity(
            base_contract,
            list(self.trackers.keys()),
            min_required=self._min_required,
        )
        self._job_min_ready_date = AsOfSlice.job_min_ready_date(self._ready_date_by_entity)
        self._job_has_work = bool(self._job_min_ready_date)

    def on_calendar_day(self, point: str, index: int) -> None:
        """推进时间(point) → 切数据 → 执行业务（装载由 BE 完成）。"""
        as_of = point  # 唯一时钟：BE Timeline / Orchestrator 传入的 point
        perf = self.perf

        # —— 尽早短路：全 job 尚无任何 entity 达到 min_required ——
        if (not self._job_has_work) or (
            self._job_min_ready_date and as_of < self._job_min_ready_date
        ):
            if perf is not None:
                perf.record_calendar_day(
                    any_bar=False,
                    bar_hits=0,
                    bar_misses=len(self.trackers),
                    as_of_slice_sec=0.0,
                    skipped_before_ready=True,
                )
            return

        # —— 切数据 ——
        if perf is not None:
            perf.begin("enum_as_of_slice")
        sliced_by_entity = AsOfSlice.slice_contracts(
            self.entity_contracts, as_of, perf=perf
        )
        if perf is not None:
            perf.end("enum_as_of_slice", accumulate=True)

        # —— 执行业务 ——
        for entity_id, tracker in self.trackers.items():
            ready = self._ready_date_by_entity.get(entity_id) or ""
            if (not ready) or as_of < ready:
                continue
            bar = AsOfSlice.base_bar(
                sliced_by_entity.get(entity_id, {}),
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

        # 日历优先：多数天 asof 只看 period 门闩，不必先组全宇宙 by_entity。
        calendar = self._build_calendar_view(
            as_of,
            stocks={},
            open_date_index=index,
        )
        stocks_ctx: Dict[str, Dict[str, Any]] = {}
        needs_by_entity = self._calendar_asof_needs_by_entity(
            as_of=as_of, calendar=calendar
        )
        if needs_by_entity:
            if perf is not None:
                perf.begin("enum_context_fill")
            stocks_ctx = self._build_stocks_context(
                sliced_by_entity,
                as_of=as_of,
            )
            if perf is not None:
                perf.end("enum_context_fill", accumulate=True)
            calendar = self._build_calendar_view(
                as_of,
                stocks=stocks_ctx,
                open_date_index=index,
            )

        asof_ctx = StrategyContext.fill(
            self._ctx_base,
            now=as_of,
            by_entity=stocks_ctx,
            calendar=calendar,
        )
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

        # 声明不需要市况却返回了 stocks → 回退全量组包再调一次。
        if (not needs_by_entity) and asof_result.stocks:
            if perf is not None:
                perf.begin("enum_context_fill")
            stocks_ctx = self._build_stocks_context(
                sliced_by_entity,
                as_of=as_of,
            )
            if perf is not None:
                perf.end("enum_context_fill", accumulate=True)
            calendar = self._build_calendar_view(
                as_of,
                stocks=stocks_ctx,
                open_date_index=index,
            )
            asof_ctx = StrategyContext.fill(
                self._ctx_base,
                now=as_of,
                by_entity=stocks_ctx,
                calendar=calendar,
            )
            if perf is not None:
                perf.begin("enum_calendar_asof")
            asof_result = self.hook_runtime.call("on_calendar_asof", asof_ctx)
            if perf is not None:
                perf.end("enum_calendar_asof", accumulate=True)
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
                tracker.settle_incomplete(
                    as_of,
                    bar,
                    reason=ExitReason.PERIOD_END.value,
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
                sliced_by_entity=sliced_by_entity,
                calendar=calendar,
                open_dates=open_dates_tuple,
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
        logger.info(
            "slice 执行完成：opportunities_count=%d",
            opportunities_count,
        )
        return {
            "success": True,
            "opportunities_count": opportunities_count,
            "entities_with_opportunities": self.entities_with_investments(),
            "entities_count": len(self.entity_ids),
        }

    def _calendar_asof_needs_by_entity(
        self, *, as_of: str, calendar: Dict[str, Any]
    ) -> bool:
        """Decide whether to build full by_entity before on_calendar_asof."""
        if not self.hook_runtime.is_overridden("on_calendar_asof"):
            return False
        probe_ctx = StrategyContext.fill(
            self._ctx_base,
            now=as_of,
            by_entity={},
            calendar=calendar,
        )
        try:
            return bool(
                self.hook_runtime.call("calendar_asof_needs_by_entity", probe_ctx)
            )
        except Exception:
            return True

    def _scan_entity(
        self,
        *,
        tracker: InvestmentTracker,
        entity_id: str,
        as_of: str,
        sliced_by_entity: Dict[str, Dict[str, Any]],
        calendar: Dict[str, Any],
        open_dates: Sequence[str],
    ) -> None:
        if tracker.has_live:
            return

        per_entity = sliced_by_entity.get(entity_id, {})
        bar = AsOfSlice.base_bar(
            per_entity,
            base_data_key=self._base_data_key,
            as_of=as_of,
            min_required=self._min_required,
        )
        if bar is None:
            return

        complete_data = dict(per_entity)
        if self.global_data:
            complete_data = {**self.global_data, **per_entity}

        stock_info = self._stock_info.get(entity_id, {"id": entity_id})
        scan_ctx = StrategyContext.fill(
            self._ctx_base,
            now=as_of,
            items=complete_data,
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
                StrategyContext.fill(
                    self._ctx_base,
                    now=as_of,
                    items=complete_data,
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
            trigger_price=SafeBarValue.float(bar, "close"),
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

    def _build_stocks_context(
        self,
        sliced_by_entity: Dict[str, Dict[str, Any]],
        *,
        as_of: str,
    ) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        for entity_id in self.entity_ids:
            per_entity = sliced_by_entity.get(entity_id, {})
            if (
                AsOfSlice.base_bar(
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
        _ = stocks  # 全市场 payload 在 StrategyData.by_entity
        return {
            "as_of_date": as_of,
            "session_state": dict(self._session_state),
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
        allowed = {"close", "open", "next_open", "touch"}
        if model and model not in allowed:
            raise ValueError(
                f"slice_based simulation.assumption.tradability.enter_price"
                f" 非法: {model!r}；允许 {sorted(allowed)}"
            )


_STATE_KEY = "_slice_task_state"
_TIMELINE_KEY = "_slice_timeline"


class EnumSliceJobExecutor(BaseJobExecutor):
    """slice_based BE 钩子 — 日历日 asof / Investment。

    边界:
    - 负责: RunCallbacks；把 SliceTaskState 写入 ``job_context.init``
    - 不负责: EnumSliceJobBuilder；BE 片窗装载 / Timeline 调度循环
    - 调用方: EnumeratorPipeline → BacktestEngine.slice_based
    """

    task_log_label = "slice task"

    @classmethod
    def on_before_all_tasks_start(cls, plan: Any, batches: List[Any]) -> None:
        print(
            f"  调度: {len(batches)} batches",
            flush=True,
        )

    @classmethod
    def on_task_start(cls, job_context: Any) -> Dict[str, Any]:
        """Task / run 准备：首次装 globals + state；之后复用 init。

        BE 会在正式片循环前先调一次（contracts 可能仍空），以便 RSS baseline
        不含 globals；每片 load 后再调一次（已有 state 则直接返回）。
        """
        from core.modules.strategy.core.services.entity_loader.job_bundle_loader import (
            JobBundleLoader,
        )
        from core.modules.strategy.core.engines.enumerator.common.performance_tracker.performance_tracker import (
            EnumJobPerfRecorder,
        )

        init = job_context.init if isinstance(job_context.init, dict) else {}
        if _STATE_KEY in init:
            return init

        logger.info("%s开始：job_id=%s（globals only）", cls.task_log_label, job_context.job_id)
        perf = EnumJobPerfRecorder.attach(job_context.payload)
        perf.begin("load_data")
        global_data = JobBundleLoader.load_globals(job_context.payload)
        perf.end("load_data")
        loaded: Dict[str, Any] = {
            "entity_contracts": dict(init.get("entity_contracts") or {}),
            "global_data": global_data,
        }
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
        logger.info(
            "%s就绪：global_keys=%d",
            cls.task_log_label,
            len(global_data),
        )
        return loaded

    @classmethod
    def on_tick(cls, job_context: Any, point: str, index: int) -> None:
        """BE 日历点 → bind contracts → asof / Investment。"""
        init = job_context.init
        if not isinstance(init, dict):
            raise TypeError("job_context.init 必须是 dict（on_task_start 返回值）")
        state: SliceTaskState = init[_STATE_KEY]
        state.bind_loaded_contracts(
            init.get("entity_contracts") or {},
            global_data=init.get("global_data"),
        )
        state.on_calendar_day(point, index)

    @classmethod
    def on_task_complete(cls, job_context: Any) -> Any:
        """每片 task 结束：更新进度；最后一片 settle + flush。"""
        init = job_context.init
        if not isinstance(init, dict):
            raise TypeError("job_context.init 必须是 dict（on_task_start 返回值）")

        try:
            from core.modules.strategy.core.services.progress import PipelineProgress

            if PipelineProgress.drives_pipeline(cls.progress_pipeline_name or ""):
                done = int(init.get("_task_index") or 0)
                total = int(init.get("_task_total") or 0)
                PipelineProgress.tick_execute_bound(done, total)
        except Exception:
            logger.exception("PipelineProgress.tick_execute_bound failed (slice)")

        done = int(init.get("_task_index") or 0)
        total = int(init.get("_task_total") or 0)
        is_last = total > 0 and done >= total
        if not is_last:
            return None

        state: SliceTaskState = init[_STATE_KEY]
        timeline = init.get(_TIMELINE_KEY)
        out = state.finalize(timeline)
        cls.flush_job_investments(job_context)
        return out if isinstance(out, dict) else {}


__all__ = ["ExecutorHooksContext", "SliceTaskState", "EnumSliceJobExecutor"]
