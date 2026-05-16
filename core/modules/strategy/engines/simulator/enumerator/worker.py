#!/usr/bin/env python3
from typing import Any, Dict, List, Optional
import logging
import time

from core.modules.data_contract.cache import ContractCacheManager
from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
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
    trade_theoretical_price,
)
from core.modules.strategy.engines.shared.helpers.strategy_runtime import resolve_worker_class
from core.modules.strategy.engines.shared.performance_profiler import PerformanceProfiler
from core.modules.strategy.enums import ExecutionMode, OpportunityStatus
from core.modules.strategy.services.data import StrategyDataInjectionService
from core.modules.strategy.services.data.output import EnumeratorOutputWriterService
from core.utils.date.date_utils import DateUtils

logger = logging.getLogger(__name__)

MAX_LOOKBACK_DAYS = 60


class OpportunityEnumeratorWorker:
    def __init__(self, job_payload: Dict[str, Any]):
        self.job_payload = job_payload
        self.stock_id = job_payload["stock_id"]
        self.strategy_name = job_payload["strategy_name"]
        self.start_date = job_payload["start_date"]
        self.end_date = job_payload["end_date"]
        self.profiler = PerformanceProfiler(self.stock_id)
        self.settings = StrategySettingsView.from_dict(job_payload["settings"])
        self.settings_dict = self.settings.to_dict()
        self.stock_info = {"id": self.stock_id, "name": self.stock_id, "industry": "", "type": "", "exchange_center": ""}
        self.contract_cache = ContractCacheManager()
        self.data_manager = StrategyDataInjectionService(
            stock_id=self.stock_id,
            settings=self.settings,
            contract_cache=self.contract_cache,
            global_extra_cache=self.job_payload.get("global_extra_cache"),
        )
        self.opportunity_counter = 0
        self.simulation = self.settings.simulation_settings
        self._load_user_strategy()

    def _load_user_strategy(self):
        strategy_class = resolve_worker_class(
            self.strategy_name,
            worker_module_path=self.job_payload.get("worker_module_path"),
            worker_class_name=self.job_payload.get("worker_class_name"),
        )
        self.strategy_instance = strategy_class(
            {
                "stock_id": self.stock_id,
                "execution_mode": ExecutionMode.SCAN.value,
                "strategy_name": self.strategy_name,
                "settings": self.settings_dict,
            }
        )
        if hasattr(self.strategy_instance, "stock_info"):
            self.strategy_instance.stock_info = self.stock_info

    def run(self) -> Dict[str, Any]:
        self.profiler.start_timer("total")
        try:
            # step1: prepare query time range
            actual_start_date = self._prepare_actual_start_date()
            # step2: load declared data into injection service
            self._load_runtime_data(actual_start_date)
            # step3: enumerate opportunities over kline timeline
            all_klines = self.data_manager.get_klines()
            if not all_klines or len(all_klines) < self.settings.min_required_records:
                bundle = self._empty_enumeration_report_bundle()
                return {
                    "success": True,
                    "stock_id": self.stock_id,
                    "opportunity_count": 0,
                    "completed_count": 0,
                    "unfinished_count": 0,
                    "stock_name": str((self.stock_info or {}).get("name") or self.stock_id),
                    "completion_rate": 0.0,
                    "avg_opportunity_interval_days": 0.0,
                    "enumeration_report_bundle": bundle,
                }
            tracker = self._enumerate_opportunities(all_klines)
            # step4: serialize opportunity objects
            opportunities_dict = self._serialize_opportunities(tracker)
            # step5: persist outputs and finalize metrics
            return self._finalize_success_result(all_klines, opportunities_dict)
        except Exception as exc:
            logger.error("enumeration failed: stock_id=%s, error=%s", self.stock_id, exc, exc_info=True)
            return {
                "success": False,
                "stock_id": self.stock_id,
                "opportunity_count": 0,
                "completed_count": 0,
                "unfinished_count": 0,
                "stock_name": str((self.stock_info or {}).get("name") or self.stock_id),
                "completion_rate": 0.0,
                "avg_opportunity_interval_days": 0.0,
                "enumeration_report_bundle": self._empty_enumeration_report_bundle(),
                "error": str(exc),
            }

    def _prepare_actual_start_date(self) -> str:
        lookback_days = min(self.settings.min_required_records, MAX_LOOKBACK_DAYS)
        return self._get_date_before(self.start_date, lookback_days)

    def _load_runtime_data(self, actual_start_date: str) -> None:
        self.profiler.start_timer("load_data")
        if "_preloaded_klines" in self.job_payload:
            self.data_manager.preload_klines(
                self.job_payload["_preloaded_klines"],
                start_date=actual_start_date,
                end_date=self.end_date,
            )
            self.data_manager.apply_indicators()
            extras = getattr(self.settings, "extra_required_data_sources", []) or []
            if extras:
                query_start = time.perf_counter()
                self.data_manager.load_declared_items(
                    extras,
                    start_date=actual_start_date,
                    end_date=self.end_date,
                )
                query_elapsed = time.perf_counter() - query_start
                for _ in range(len(extras)):
                    self.profiler.record_db_query(query_elapsed / max(len(extras), 1))
            self.data_manager.rebuild_data_cursor()
        else:
            query_start = time.perf_counter()
            self.data_manager.load_historical_data(
                start_date=actual_start_date, end_date=self.end_date
            )
            query_elapsed = time.perf_counter() - query_start
            required_sources = getattr(self.settings, "required_data_sources", []) or []
            estimated = max(len(required_sources), 1)
            for _ in range(estimated):
                self.profiler.record_db_query(query_elapsed / estimated)
        self.profiler.metrics.time_load_data = self.profiler.end_timer("load_data")

    def _enumerate_opportunities(self, all_klines: List[Dict[str, Any]]) -> Dict[str, Any]:
        tracker = {
            "stock_id": self.stock_id,
            "passed_dates": [],
            "pending_buys": [],
            "active_opportunities": [],
            "all_opportunities": [],
        }
        self.profiler.start_timer("enumerate")
        last_kline = None
        for idx, current_kline in enumerate(all_klines):
            virtual_date_of_today = current_kline["date"]
            tracker["passed_dates"].append(virtual_date_of_today)
            if len(tracker["passed_dates"]) < self.settings.min_required_records:
                continue
            data_of_today = self.data_manager.get_data_until(virtual_date_of_today)
            self._enumerate_single_day(tracker, current_kline, data_of_today)
            last_kline = current_kline
        self.profiler.metrics.time_enumerate = self.profiler.end_timer("enumerate")
        if last_kline is not None:
            resolve_pending_buys_at_end(
                tracker["pending_buys"],
                tracker["active_opportunities"],
                tracker["all_opportunities"],
                sim=self.simulation,
            )
            resolve_pending_exits_on_active_at_end(
                tracker["active_opportunities"],
                last_bar=last_kline,
                sim=self.simulation,
            )
            if tracker["active_opportunities"]:
                self._close_all_open_opportunities(tracker, last_kline)
        return tracker

    def _serialize_opportunities(self, tracker: Dict[str, Any]) -> List[Dict[str, Any]]:
        self.profiler.start_timer("serialize")
        opportunities_dict = [opportunity.to_dict() for opportunity in tracker["all_opportunities"]]
        self.profiler.metrics.time_serialize = self.profiler.end_timer("serialize")
        return opportunities_dict

    def _finalize_success_result(
        self,
        all_klines: List[Dict[str, Any]],
        opportunities_dict: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if self.job_payload.get("output_dir") and opportunities_dict:
            self.profiler.start_timer("save_csv")
            self._save_stock_results(self.job_payload["output_dir"], opportunities_dict)
            self.profiler.metrics.time_save_csv = self.profiler.end_timer("save_csv")
        self.profiler.metrics.kline_count = len(all_klines)
        self.profiler.metrics.opportunity_count = len(opportunities_dict)
        self.profiler.metrics.target_count = sum(
            len(opportunity.get("completed_targets", []) or [])
            for opportunity in opportunities_dict
        )
        completed_count = 0
        unfinished_count = 0
        for opportunity in opportunities_dict:
            sell_reason = str(opportunity.get("sell_reason", "") or "").lower()
            if sell_reason in {"enumeration_end", "backtest_end"}:
                unfinished_count += 1
            else:
                # 兜底：若未写 sell_reason 但仍显示持仓态，仍视为未完成
                status = str(opportunity.get("status", "") or "").lower()
                if status in {"open", "active", "testing"}:
                    unfinished_count += 1
                else:
                    completed_count += 1
        self.profiler.metrics.time_total = self.profiler.end_timer("total")
        metrics = self.profiler.finalize()
        n = len(opportunities_dict)
        completion_rate = round((completed_count / n) * 100.0, 1) if n else 0.0
        avg_gap = self._avg_trigger_gap_days(opportunities_dict)
        display_name = str((self.stock_info or {}).get("name") or self.stock_id)
        enum_bundle = self._build_enumeration_report_bundle(opportunities_dict)
        return {
            "success": True,
            "stock_id": self.stock_id,
            "stock_name": display_name,
            "opportunity_count": n,
            "completed_count": completed_count,
            "unfinished_count": unfinished_count,
            "completion_rate": completion_rate,
            "avg_opportunity_interval_days": avg_gap,
            "performance_metrics": metrics.to_dict(),
            "enumeration_report_bundle": enum_bundle,
        }

    def _empty_enumeration_report_bundle(self) -> Dict[str, Any]:
        display_name = str((self.stock_info or {}).get("name") or self.stock_id)
        return {
            "stock_name": display_name,
            "opportunity_count": 0,
            "report_completed_count": 0,
            "report_unfinished_count": 0,
            "status_completed_count": 0,
            "trigger_gap_days": [],
            "holding_duration_days": [],
        }

    def _build_enumeration_report_bundle(self, opportunities_dict: List[Dict[str, Any]]) -> Dict[str, Any]:
        """供主进程汇总 ``enumMetrics``，避免再读该股 CSV。字段语义与 ``EnumeratorReport.from_opportunities`` 一致。"""
        display_name = str((self.stock_info or {}).get("name") or self.stock_id)
        if not opportunities_dict:
            return {
                **self._empty_enumeration_report_bundle(),
                "stock_name": display_name,
            }
        report_completed = 0
        report_unfinished = 0
        for opportunity in opportunities_dict:
            sell_reason = str(opportunity.get("sell_reason", "") or "").lower()
            if sell_reason in {"enumeration_end", "backtest_end"}:
                report_unfinished += 1
            else:
                status = str(opportunity.get("status", "") or "").lower()
                if status in {"open", "active", "testing"}:
                    report_unfinished += 1
                else:
                    report_completed += 1
        status_completed = sum(
            1 for o in opportunities_dict if str((o or {}).get("status") or "").lower() == "completed"
        )
        sorted_rows = sorted(
            opportunities_dict,
            key=lambda r: str((r or {}).get("trigger_date") or ""),
        )
        trigger_dates: List[str] = []
        for r in sorted_rows:
            d = DateUtils.normalize_str(str((r or {}).get("trigger_date") or ""))
            if isinstance(d, str) and d:
                trigger_dates.append(d)
        gaps: List[float] = []
        for idx in range(1, len(trigger_dates)):
            gaps.append(float(DateUtils.diff_days(trigger_dates[idx - 1], trigger_dates[idx])))
        durations: List[float] = []
        for r in sorted_rows:
            d0 = DateUtils.normalize_str(str((r or {}).get("trigger_date") or ""))
            d1 = DateUtils.normalize_str(str((r or {}).get("sell_date") or ""))
            if d0 and d1:
                durations.append(float(DateUtils.diff_days(d0, d1)))
        return {
            "stock_name": display_name,
            "opportunity_count": len(opportunities_dict),
            "report_completed_count": report_completed,
            "report_unfinished_count": report_unfinished,
            "status_completed_count": status_completed,
            "trigger_gap_days": gaps,
            "holding_duration_days": durations,
        }

    @staticmethod
    def _avg_trigger_gap_days(opportunities_dict: List[Dict[str, Any]]) -> float:
        """相邻两次机会触发日（trigger_date）之间的间隔天数均值；不足 2 个触发则 0。"""
        if not opportunities_dict or len(opportunities_dict) < 2:
            return 0.0
        sorted_rows = sorted(
            opportunities_dict,
            key=lambda r: str((r or {}).get("trigger_date") or ""),
        )
        trigger_dates: List[str] = []
        for r in sorted_rows:
            d = DateUtils.normalize_str(str((r or {}).get("trigger_date") or ""))
            if isinstance(d, str) and d:
                trigger_dates.append(d)
        if len(trigger_dates) < 2:
            return 0.0
        gaps: List[float] = []
        for idx in range(1, len(trigger_dates)):
            gaps.append(float(DateUtils.diff_days(trigger_dates[idx - 1], trigger_dates[idx])))
        return round(sum(gaps) / len(gaps), 1) if gaps else 0.0

    def _get_date_before(self, date_str: str, days: int) -> str:
        try:
            return DateUtils.sub_days(date_str, days)
        except Exception:
            return date_str

    def _enumerate_single_day(
        self,
        tracker: Dict[str, Any],
        current_kline: Dict[str, Any],
        data_of_today: Dict[str, Any],
    ):
        fill_pending_buys(
            tracker["pending_buys"],
            tracker["active_opportunities"],
            bar=current_kline,
            sim=self.simulation,
        )
        exit_indices = execute_pending_exits_on_active(
            tracker["active_opportunities"],
            bar=current_kline,
            sim=self.simulation,
        )
        for idx in reversed(exit_indices):
            tracker["active_opportunities"].pop(idx)

        completed_indices = []
        for idx, opportunity in enumerate(tracker["active_opportunities"]):
            if opportunity.check_targets(
                self.simulation,
                current_kline=current_kline,
                goal_config=self.settings.goal,
            ):
                completed_indices.append(idx)
        for idx in reversed(completed_indices):
            tracker["active_opportunities"].pop(idx)

        opportunity = self._scan_opportunity_with_data(data_of_today)
        if not opportunity:
            return
        if opportunity.stock:
            opportunity.stock = {**self.stock_info, **opportunity.stock}
        else:
            opportunity.stock = self.stock_info
        opportunity.stock_id = self.stock_id
        opportunity.strategy_name = self.strategy_name
        opportunity.trigger_date = current_kline["date"]
        opportunity.trigger_price = float(current_kline.get("close") or 0.0)
        opportunity.completed_targets = []
        self.opportunity_counter += 1
        opportunity.opportunity_id = str(self.opportunity_counter)
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

        buy_raw = trade_theoretical_price(
            self.simulation.buy_price_model,
            side="buy",
            bar=current_kline,
            no_next_bar=self.simulation.edges_no_next_bar,
        )
        if buy_raw is None:
            tracker["all_opportunities"].pop()
            return
        opportunity.buy_price = apply_buy_slippage(buy_raw, self.simulation.slippage_buy_bps)
        opportunity.buy_date = str(current_kline.get("date") or opportunity.trigger_date)
        opportunity.status = OpportunityStatus.ACTIVE.value
        tracker["active_opportunities"].append(opportunity)

    def _scan_opportunity_with_data(self, data: Dict[str, Any]):
        return self.strategy_instance.scan_opportunity(data, self.settings_dict)

    def _close_all_open_opportunities(
        self,
        tracker: Dict[str, Any],
        last_kline: Dict[str, Any],
    ):
        for opportunity in tracker["active_opportunities"]:
            opportunity.settle(
                self.simulation,
                last_kline=last_kline,
                reason="enumeration_end",
            )
        tracker["active_opportunities"].clear()

    def _save_stock_results(self, output_dir: str, opportunities: List[Dict[str, Any]]):
        from pathlib import Path

        output_path = Path(output_dir)
        opportunity_rows, target_rows = EnumeratorOutputWriterService.build_stock_rows(
            opportunities=opportunities
        )
        EnumeratorOutputWriterService.write_stock_csv(
            output_dir=output_path,
            stock_id=self.stock_id,
            opportunity_rows=opportunity_rows,
            target_rows=target_rows,
        )


__all__ = ["OpportunityEnumeratorWorker"]
