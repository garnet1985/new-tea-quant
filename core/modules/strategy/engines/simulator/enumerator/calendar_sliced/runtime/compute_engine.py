#!/usr/bin/env python3
"""calendar_slice Compute Lane：策略 + holdings + scan（无 DB）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging

from core.modules.data_contract.cache import ContractCacheManager
from core.modules.indicator import IndicatorService
from core.modules.market_profile import get_market_profile
from core.modules.strategy.base_strategy_worker import BaseStrategyWorker
from core.modules.strategy.engines.shared.data_classes.investment_state import (
    InvestmentLifecycle,
    ScanSignalPhase,
)
from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)
from core.modules.strategy.engines.shared.helpers.backtest_calendar_context import (
    BacktestCalendarContext,
)
from core.modules.strategy.engines.shared.helpers.market_profile_id import (
    resolve_market_profile_id,
)
from core.modules.strategy.engines.shared.helpers.simulation_day_execution import (
    execute_pending_exits_on_active,
    fill_pending_buys,
    queue_deferred_buy,
    resolve_pending_buys_at_end,
    resolve_pending_exits_on_active_at_end,
)
from core.modules.strategy.engines.shared.helpers.simulation_pricing import (
    apply_buy_slippage,
    trade_price_defers_to_next_session,
    trade_theoretical_price_same_day,
)
from core.modules.strategy.engines.shared.helpers.skip_investment_when import (
    stamp_stock_status_at_trigger,
)
from core.modules.strategy.engines.shared.helpers.stock_status_risk_context import (
    StockStatusRiskRuntimeContext,
    build_stock_status_risk_runtime_context,
)
from core.modules.strategy.engines.shared.helpers.strategy_runtime import resolve_worker_class
from core.modules.strategy.engines.shared.helpers.tradability import stamp_buy_tradability
from core.modules.strategy.engines.shared.helpers.tradability_stats import (
    tradability_bundle_from_opportunities,
)
from core.modules.strategy.engines.shared.performance_profiler import PerformanceProfiler
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.progress import (
    CALENDAR_PROGRESS_MODE_OPEN_DATE,
    CALENDAR_PROGRESS_MODE_SLICE,
    CalendarSliceProgressReporter,
    normalize_calendar_progress_mode,
    resolve_calendar_progress_plan,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.batch_transfer import (
    transfer_to_batch,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.messages import (
    SlicePayload,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.slice_plan import (
    CalendarSliceDescriptor,
    is_first_open_of_month,
    is_first_open_of_year,
    is_last_open_of_month,
    is_last_open_of_year,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.types import (
    CalendarAsOfContext,
    CalendarAsOfResult,
)
from core.modules.strategy.enums import ExecutionMode
from core.modules.strategy.services.data import StrategyDataInjectionService
from core.modules.strategy.services.data.output import EnumeratorOutputWriterService
from core.utils.date.date_utils import DateUtils

logger = logging.getLogger(__name__)

_indicator_runtime_warmed = False


def warmup_indicator_runtime_once() -> None:
    global _indicator_runtime_warmed
    if _indicator_runtime_warmed:
        return
    IndicatorService.warmup()
    _indicator_runtime_warmed = True


@dataclass
class StockEnumState:
    stock_id: str
    stock_info: Dict[str, Any]
    data_manager: StrategyDataInjectionService
    stock_status_risk: StockStatusRiskRuntimeContext
    tracker: Dict[str, Any] = field(default_factory=dict)
    opportunity_counter: int = 0


class CalendarSliceComputeEngine:
    """消费 SlicePayload，执行 on_calendar_asof / scan_opportunity 循环。"""

    def __init__(self, job_payload: Dict[str, Any]):
        self.job_payload = job_payload
        self.stock_ids = [
            str(s).strip() for s in (job_payload.get("stock_ids") or []) if str(s).strip()
        ]
        if not self.stock_ids:
            raise ValueError("CalendarSliceComputeEngine 缺少 stock_ids")
        self.strategy_name = job_payload["strategy_name"]
        self.start_date = str(job_payload["start_date"])
        self.end_date = str(job_payload["end_date"])
        raw_slice = job_payload.get("slice_open_days")
        if not isinstance(raw_slice, int):
            raise ValueError(
                f"compute lane 需要 orchestrator 已 resolve 的 slice_open_days 整数，收到 {raw_slice!r}"
            )
        self.slice_open_days = raw_slice
        self.settings = StrategySettingsView.from_dict(job_payload["settings"])
        self.settings_dict = self.settings.to_dict()
        self.simulation = self.settings.simulation_settings
        profile_id = resolve_market_profile_id(
            job_payload,
            settings_market_profile=self.settings.market_profile,
        )
        self.market_profile = get_market_profile(profile_id)
        self.backtest_calendar = BacktestCalendarContext.from_dict(
            job_payload.get("backtest_calendar")
        )
        self.contract_cache = ContractCacheManager()
        self.profiler = PerformanceProfiler("calendar_slice")
        self._stock_infos = self._resolve_stock_infos()
        self._load_user_strategy()
        self._states: Dict[str, StockEnumState] = {}
        self._last_kline_by_stock: Dict[str, Dict[str, Any]] = {}

    def _resolve_stock_infos(self) -> Dict[str, Dict[str, Any]]:
        raw = self.job_payload.get("stock_infos")
        if isinstance(raw, dict) and raw:
            out: Dict[str, Dict[str, Any]] = {}
            for sid in self.stock_ids:
                info = raw.get(sid)
                if isinstance(info, dict):
                    out[sid] = {**info, "id": sid}
                else:
                    out[sid] = {"id": sid, "name": sid}
            return out
        return {sid: {"id": sid, "name": sid} for sid in self.stock_ids}

    def _load_user_strategy(self) -> None:
        strategy_class = resolve_worker_class(
            self.strategy_name,
            worker_module_path=self.job_payload.get("worker_module_path"),
            worker_class_name=self.job_payload.get("worker_class_name"),
            worker_file_path=str(self.job_payload.get("worker_file_path") or ""),
        )
        anchor_id = self.stock_ids[0]
        self.strategy_instance = strategy_class(
            {
                "stock_id": anchor_id,
                "execution_mode": ExecutionMode.SCAN.value,
                "strategy_name": self.strategy_name,
                "settings": self.settings_dict,
            }
        )
        if hasattr(self.strategy_instance, "stock_info"):
            self.strategy_instance.stock_info = self._stock_infos[anchor_id]

    def create_progress_reporter(
        self,
        open_dates: List[str],
        *,
        run_started_at: float,
    ) -> Optional[CalendarSliceProgressReporter]:
        total = int(self.job_payload.get("calendar_progress_total") or 0)
        mode = normalize_calendar_progress_mode(
            self.job_payload.get("calendar_progress_mode")
        )
        if total <= 0:
            plan = resolve_calendar_progress_plan(
                open_dates=open_dates,
                slice_open_days=self.slice_open_days,
                progress_mode=mode,
            )
            total = int(plan["calendar_progress_total"])
            mode = str(plan["calendar_progress_mode"])
        return CalendarSliceProgressReporter(
            self.job_payload,
            total=total,
            mode=mode,
            run_started_at=run_started_at,
        )

    def run_slice(
        self,
        payload: SlicePayload,
        carry: Dict[str, Any],
        *,
        reporter: Optional[CalendarSliceProgressReporter] = None,
    ) -> Dict[str, Any]:
        slice_desc = CalendarSliceDescriptor(
            slice_id=payload.slice_id,
            slice_index=payload.slice_index,
            window_start=payload.window_start,
            window_end=payload.window_end,
            open_dates=payload.open_dates,
        )
        job_batch = transfer_to_batch(payload.batch_transfer)
        for sid in self.stock_ids:
            state = self._states.get(sid)
            if state is None:
                dm = StrategyDataInjectionService(
                    stock_id=sid,
                    settings=self.settings,
                    contract_cache=self.contract_cache,
                    global_extra_cache=self.job_payload.get("global_extra_cache"),
                )
                state = StockEnumState(
                    stock_id=sid,
                    stock_info=self._stock_infos[sid],
                    data_manager=dm,
                    stock_status_risk=build_stock_status_risk_runtime_context(
                        stock_meta=self._stock_infos[sid],
                        settings=self.settings.stock_status_risk,
                        stock_id=sid,
                        period_start=self.start_date,
                        period_end=self.end_date,
                    ),
                    tracker=self._empty_tracker(sid),
                )
                self._states[sid] = state
            dm = state.data_manager
            dm.adopt_job_batch(job_batch)
            dm.apply_indicators()
            dm.rebuild_data_cursor()

        all_open_dates = self.backtest_calendar.open_dates if self.backtest_calendar else ()
        for open_date_index, as_of in enumerate(slice_desc.open_dates):
            for state in self._states.values():
                if self._has_bar_on(state, as_of):
                    self._advance_holdings_for_day(state, as_of)

            stocks_ctx = self._build_stocks_context(as_of)
            ctx = CalendarAsOfContext(
                as_of_date=as_of,
                slice_id=slice_desc.slice_id,
                slice_open_days=self.slice_open_days,
                window_start=slice_desc.window_start,
                window_end=slice_desc.window_end,
                stocks=stocks_ctx,
                carry=carry,
                open_date_index=open_date_index,
                is_first_open_of_month=is_first_open_of_month(as_of, all_open_dates),
                is_last_open_of_month=is_last_open_of_month(as_of, all_open_dates),
                is_first_open_of_year=is_first_open_of_year(as_of, all_open_dates),
                is_last_open_of_year=is_last_open_of_year(as_of, all_open_dates),
            )
            asof_result = self._call_on_calendar_asof(ctx)
            carry = dict(asof_result.carry or {})
            force_exit_date = str(carry.get("force_exit_open_date") or "").strip()
            if force_exit_date and force_exit_date == as_of:
                for state in self._states.values():
                    self._force_exit_active_on_bar(state, as_of)
            for sid in asof_result.selected_stock_ids:
                sid_norm = str(sid or "").strip()
                if sid_norm not in self._states:
                    continue
                override = (asof_result.stock_overrides or {}).get(sid_norm) or {}
                self._scan_selected_stock(
                    self._states[sid_norm],
                    as_of,
                    stock_override=override,
                )
            if reporter is not None and reporter.mode == CALENDAR_PROGRESS_MODE_OPEN_DATE:
                reporter.tick(
                    as_of_date=as_of,
                    slice_id=slice_desc.slice_id,
                    phase="open_date",
                )

        for state in self._states.values():
            state.data_manager.clear_working_state()
        if reporter is not None and reporter.mode == CALENDAR_PROGRESS_MODE_SLICE:
            reporter.tick(slice_id=slice_desc.slice_id, phase="slice_done")
        return carry

    @staticmethod
    def _empty_tracker(stock_id: str) -> Dict[str, Any]:
        return {
            "stock_id": stock_id,
            "passed_dates": [],
            "pending_buys": [],
            "active_opportunities": [],
            "all_opportunities": [],
        }

    def _build_stocks_context(self, as_of: str) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        min_records = self.settings.min_required_records
        for sid, state in self._states.items():
            data = state.data_manager.get_data_until(as_of)
            klines = data.get("klines") or []
            if not klines or str(klines[-1].get("date") or "") != as_of:
                continue
            if len(klines) < min_records:
                continue
            out[sid] = data
        return out

    def _call_on_calendar_asof(self, ctx: CalendarAsOfContext) -> CalendarAsOfResult:
        hook = getattr(self.strategy_instance, "on_calendar_asof", None)
        if callable(hook):
            raw = hook(ctx, self.settings_dict)
            if isinstance(raw, CalendarAsOfResult):
                return raw
            if isinstance(raw, dict):
                return CalendarAsOfResult(
                    selected_stock_ids=list(raw.get("selected_stock_ids") or []),
                    stock_overrides=dict(raw.get("stock_overrides") or {}),
                    carry=dict(raw.get("carry") or {}),
                )
            if isinstance(raw, (list, tuple)):
                return CalendarAsOfResult(selected_stock_ids=[str(x) for x in raw])
            raise TypeError("on_calendar_asof 须返回 CalendarAsOfResult、dict 或 stock_id 列表")
        return BaseStrategyWorker.on_calendar_asof(
            self.strategy_instance,
            ctx,
            self.settings_dict,
        )

    @staticmethod
    def _has_bar_on(state: StockEnumState, as_of: str) -> bool:
        klines = state.data_manager.get_data_until(as_of).get("klines") or []
        return bool(klines) and str(klines[-1].get("date") or "") == as_of

    def _bar_context(
        self,
        state: StockEnumState,
        as_of: str,
    ) -> Optional[tuple[Dict[str, Any], Optional[Dict[str, Any]], Dict[str, Any]]]:
        data = state.data_manager.get_data_until(as_of)
        klines = data.get("klines") or []
        if not klines or str(klines[-1].get("date") or "") != as_of:
            return None
        current_kline = klines[-1]
        idx = len(klines) - 1
        prev_kline = klines[idx - 1] if idx > 0 else None
        return current_kline, prev_kline, data

    def _advance_holdings_for_day(self, state: StockEnumState, as_of: str) -> None:
        ctx = self._bar_context(state, as_of)
        if ctx is None:
            return
        current_kline, prev_kline, _data = ctx
        self._last_kline_by_stock[state.stock_id] = current_kline
        self._process_bar_without_scan(
            state,
            state.tracker,
            current_kline,
            prev_kline=prev_kline,
        )

    def _force_exit_active_on_bar(self, state: StockEnumState, as_of: str) -> None:
        ctx = self._bar_context(state, as_of)
        if ctx is None:
            return
        current_kline, prev_kline, _data = ctx
        tracker = state.tracker
        if not tracker["active_opportunities"]:
            return
        for opportunity in list(tracker["active_opportunities"]):
            opportunity.settle(
                self.simulation,
                last_kline=current_kline,
                reason="month_end",
                market_profile=self.market_profile,
                prev_bar=prev_kline,
                stock_status_risk=state.stock_status_risk,
            )
        tracker["active_opportunities"].clear()

    def _scan_selected_stock(
        self,
        state: StockEnumState,
        as_of: str,
        *,
        stock_override: Optional[Dict[str, Any]] = None,
    ) -> None:
        ctx = self._bar_context(state, as_of)
        if ctx is None:
            return
        current_kline, prev_kline, data = ctx
        if stock_override:
            data = {**data, **stock_override}
        self._last_kline_by_stock[state.stock_id] = current_kline
        tracker = state.tracker
        if as_of not in tracker["passed_dates"]:
            tracker["passed_dates"].append(as_of)
        if len(tracker["passed_dates"]) < self.settings.min_required_records:
            return
        self._bind_strategy_stock(state)
        self._try_scan_opportunity(
            state,
            tracker,
            current_kline,
            data,
            prev_kline=prev_kline,
        )

    def _bind_strategy_stock(self, state: StockEnumState) -> None:
        self.strategy_instance.stock_id = state.stock_id
        if hasattr(self.strategy_instance, "stock_info"):
            self.strategy_instance.stock_info = state.stock_info

    def _process_bar_without_scan(
        self,
        state: StockEnumState,
        tracker: Dict[str, Any],
        current_kline: Dict[str, Any],
        *,
        prev_kline: Optional[Dict[str, Any]] = None,
    ) -> None:
        fill_pending_buys(
            tracker["pending_buys"],
            tracker["active_opportunities"],
            bar=current_kline,
            sim=self.simulation,
            market_profile=self.market_profile,
            prev_bar=prev_kline,
            stock_status_risk=state.stock_status_risk,
        )
        exit_indices = execute_pending_exits_on_active(
            tracker["active_opportunities"],
            bar=current_kline,
            sim=self.simulation,
            market_profile=self.market_profile,
            prev_bar=prev_kline,
            stock_status_risk=state.stock_status_risk,
        )
        for idx in reversed(exit_indices):
            tracker["active_opportunities"].pop(idx)

        completed_indices = []
        for idx, opportunity in enumerate(tracker["active_opportunities"]):
            if opportunity.check_targets(
                self.simulation,
                current_kline=current_kline,
                goal_config=self.settings.goal,
                market_profile=self.market_profile,
                prev_bar=prev_kline,
                backtest_calendar=self.backtest_calendar,
                stock_status_risk=state.stock_status_risk,
            ):
                completed_indices.append(idx)
        for idx in reversed(completed_indices):
            tracker["active_opportunities"].pop(idx)

    def _try_scan_opportunity(
        self,
        state: StockEnumState,
        tracker: Dict[str, Any],
        current_kline: Dict[str, Any],
        data_of_today: Dict[str, Any],
        *,
        prev_kline: Optional[Dict[str, Any]] = None,
    ) -> None:
        opportunity = self.strategy_instance.scan_opportunity(data_of_today, self.settings_dict)
        if not opportunity:
            return
        if opportunity.stock:
            opportunity.stock = {**state.stock_info, **opportunity.stock}
        else:
            opportunity.stock = state.stock_info
        opportunity.stock_id = state.stock_id
        opportunity.strategy_name = self.strategy_name
        opportunity.trigger_date = current_kline["date"]
        opportunity.trigger_price = float(current_kline.get("close") or 0.0)
        stamp_stock_status_at_trigger(
            opportunity,
            trade_date=opportunity.trigger_date,
            tier_periods=state.stock_status_risk.tier_periods,
        )
        opportunity.completed_targets = []
        state.opportunity_counter += 1
        opportunity.opportunity_id = str(state.opportunity_counter)
        opportunity.enrich_from_framework(
            strategy_name=self.strategy_name,
            strategy_version="1.0",
            opportunity_id=opportunity.opportunity_id,
        )
        tracker["all_opportunities"].append(opportunity)

        if trade_price_defers_to_next_session(self.simulation.buy_price_model):
            queue_deferred_buy(opportunity, signal_bar=current_kline)
            tracker["pending_buys"].append(opportunity)
            return

        buy_raw = trade_theoretical_price_same_day(
            self.simulation.buy_price_model,
            side="buy",
            bar=current_kline,
            no_next_bar=self.simulation.edges_no_next_bar,
        )
        if buy_raw is None:
            tracker["all_opportunities"].pop()
            return
        buy_price = apply_buy_slippage(buy_raw, self.simulation.slippage_buy_bps)
        opportunity.buy_price = buy_price
        opportunity.buy_date = str(current_kline.get("date") or "")
        stamp_buy_tradability(
            opportunity,
            self.market_profile,
            state.stock_id,
            prev_kline,
            buy_price,
            stock_status_risk=state.stock_status_risk,
            trade_date=opportunity.buy_date,
            exec_bar=current_kline,
        )
        opportunity.signal_phase = ScanSignalPhase.ACTIVE.value
        opportunity.lifecycle = InvestmentLifecycle.OPEN.value
        tracker["active_opportunities"].append(opportunity)

    def finalize_all(self) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        output_dir = self.job_payload.get("output_dir")
        for sid in self.stock_ids:
            state = self._states.get(sid)
            if state is None:
                results.append(self._stock_result_row(sid, success=True, opportunities=[]))
                continue
            tracker = state.tracker
            last_kline = self._last_kline_by_stock.get(sid)
            if last_kline is None and self.backtest_calendar is not None:
                open_dates = [
                    d
                    for d in self.backtest_calendar.open_dates
                    if self.start_date <= d <= self.end_date
                ]
                if open_dates:
                    last_kline = {"date": open_dates[-1], "close": 0.0}
            if last_kline is not None:
                resolve_pending_buys_at_end(
                    tracker["pending_buys"],
                    tracker["active_opportunities"],
                    tracker["all_opportunities"],
                    sim=self.simulation,
                    market_profile=self.market_profile,
                )
                resolve_pending_exits_on_active_at_end(
                    tracker["active_opportunities"],
                    last_bar=last_kline,
                    sim=self.simulation,
                    market_profile=self.market_profile,
                )
                if tracker["active_opportunities"]:
                    self._close_all_open_opportunities(state, tracker, last_kline)
            opportunities_dict = [
                opportunity.to_dict() for opportunity in tracker["all_opportunities"]
            ]
            if output_dir and opportunities_dict:
                self._save_stock_results(str(output_dir), sid, opportunities_dict)
            results.append(
                self._stock_result_row(
                    sid,
                    success=True,
                    opportunities=opportunities_dict,
                    stock_name=str(state.stock_info.get("name") or sid),
                )
            )
        return results

    def _close_all_open_opportunities(
        self,
        state: StockEnumState,
        tracker: Dict[str, Any],
        last_kline: Dict[str, Any],
    ) -> None:
        for opportunity in tracker["active_opportunities"]:
            opportunity.settle(
                self.simulation,
                last_kline=last_kline,
                reason="enumeration_end",
                market_profile=self.market_profile,
                stock_status_risk=state.stock_status_risk,
            )
        tracker["active_opportunities"].clear()

    def _save_stock_results(
        self,
        output_dir: str,
        stock_id: str,
        opportunities: List[Dict[str, Any]],
    ) -> None:
        from pathlib import Path

        output_path = Path(output_dir)
        opportunity_rows, target_rows = EnumeratorOutputWriterService.build_stock_rows(
            opportunities=opportunities
        )
        EnumeratorOutputWriterService.write_stock_csv(
            output_dir=output_path,
            stock_id=stock_id,
            opportunity_rows=opportunity_rows,
            target_rows=target_rows,
        )

    def _stock_result_row(
        self,
        stock_id: str,
        *,
        success: bool,
        opportunities: List[Dict[str, Any]],
        stock_name: Optional[str] = None,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        display_name = stock_name or str(self._stock_infos.get(stock_id, {}).get("name") or stock_id)
        n = len(opportunities)
        completed_count = 0
        unfinished_count = 0
        for opportunity in opportunities:
            sell_reason = str(opportunity.get("sell_reason", "") or "").lower()
            if sell_reason in {"enumeration_end", "backtest_end"}:
                unfinished_count += 1
            else:
                lifecycle = str(opportunity.get("lifecycle", "") or "").lower()
                phase = str(opportunity.get("signal_phase", "") or "").lower()
                if (
                    lifecycle == InvestmentLifecycle.OPEN.value
                    or phase in {ScanSignalPhase.ACTIVE.value, ScanSignalPhase.TESTING.value}
                ):
                    unfinished_count += 1
                else:
                    completed_count += 1
        completion_rate = round((completed_count / n) * 100.0, 1) if n else 0.0
        avg_gap = self._avg_trigger_gap_days(opportunities)
        enum_bundle = (
            self._build_enumeration_report_bundle(display_name, opportunities)
            if opportunities
            else self._empty_enumeration_report_bundle(display_name)
        )
        row: Dict[str, Any] = {
            "success": success,
            "stock_id": stock_id,
            "stock_name": display_name,
            "opportunity_count": n,
            "completed_count": completed_count,
            "unfinished_count": unfinished_count,
            "completion_rate": completion_rate,
            "avg_opportunity_interval_days": avg_gap,
            "enumeration_report_bundle": enum_bundle,
        }
        if error:
            row["error"] = error
        return row

    @staticmethod
    def _avg_trigger_gap_days(opportunities: List[Dict[str, Any]]) -> float:
        if not opportunities or len(opportunities) < 2:
            return 0.0
        sorted_rows = sorted(
            opportunities,
            key=lambda r: str((r or {}).get("trigger_date") or ""),
        )
        trigger_dates: List[str] = []
        for row in sorted_rows:
            d = DateUtils.normalize_str(str((row or {}).get("trigger_date") or ""))
            if isinstance(d, str) and d:
                trigger_dates.append(d)
        if len(trigger_dates) < 2:
            return 0.0
        gaps = [
            float(DateUtils.diff_days(trigger_dates[i - 1], trigger_dates[i]))
            for i in range(1, len(trigger_dates))
        ]
        return round(sum(gaps) / len(gaps), 1) if gaps else 0.0

    @staticmethod
    def _empty_enumeration_report_bundle(stock_name: str) -> Dict[str, Any]:
        return {
            "stock_name": stock_name,
            "opportunity_count": 0,
            "report_completed_count": 0,
            "report_unfinished_count": 0,
            "status_completed_count": 0,
            "trigger_gap_days": [],
            "holding_duration_days": [],
            "buy_tradability_sample_count": 0,
            "buy_at_limit_up_count": 0,
            "sell_tradability_sample_count": 0,
            "sell_at_limit_down_count": 0,
            "limit_up_buy_ratio": 0.0,
            "limit_down_sell_ratio": 0.0,
        }

    def _build_enumeration_report_bundle(
        self,
        stock_name: str,
        opportunities: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not opportunities:
            return self._empty_enumeration_report_bundle(stock_name)
        report_completed = 0
        report_unfinished = 0
        for opportunity in opportunities:
            sell_reason = str(opportunity.get("sell_reason", "") or "").lower()
            if sell_reason in {"enumeration_end", "backtest_end"}:
                report_unfinished += 1
            else:
                lifecycle = str(opportunity.get("lifecycle", "") or "").lower()
                phase = str(opportunity.get("signal_phase", "") or "").lower()
                if (
                    lifecycle == InvestmentLifecycle.OPEN.value
                    or phase in {ScanSignalPhase.ACTIVE.value, ScanSignalPhase.TESTING.value}
                ):
                    report_unfinished += 1
                else:
                    report_completed += 1
        status_completed = sum(
            1
            for o in opportunities
            if str((o or {}).get("lifecycle") or "").lower() == InvestmentLifecycle.COMPLETE.value
        )
        sorted_rows = sorted(
            opportunities,
            key=lambda r: str((r or {}).get("trigger_date") or ""),
        )
        trigger_dates: List[str] = []
        for row in sorted_rows:
            d = DateUtils.normalize_str(str((row or {}).get("trigger_date") or ""))
            if isinstance(d, str) and d:
                trigger_dates.append(d)
        gaps = [
            float(DateUtils.diff_days(trigger_dates[i - 1], trigger_dates[i]))
            for i in range(1, len(trigger_dates))
        ]
        durations: List[float] = []
        for row in sorted_rows:
            d0 = DateUtils.normalize_str(str((row or {}).get("trigger_date") or ""))
            d1 = DateUtils.normalize_str(str((row or {}).get("sell_date") or ""))
            if d0 and d1:
                durations.append(float(DateUtils.diff_days(d0, d1)))
        return {
            "stock_name": stock_name,
            "opportunity_count": len(opportunities),
            "report_completed_count": report_completed,
            "report_unfinished_count": report_unfinished,
            "status_completed_count": status_completed,
            "trigger_gap_days": gaps,
            "holding_duration_days": durations,
            **tradability_bundle_from_opportunities(opportunities),
        }


__all__ = ["CalendarSliceComputeEngine", "StockEnumState", "warmup_indicator_runtime_once"]
