#!/usr/bin/env python3
from typing import Any, Dict, List
import logging
import time

from core.modules.data_contract.cache import ContractCacheManager
from core.modules.strategy.engines.shared.data_classes.opportunity import Opportunity
from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)
from core.modules.strategy.engines.shared.helpers.strategy_runtime import resolve_worker_class
from core.modules.strategy.engines.shared.performance_profiler import PerformanceProfiler
from core.modules.strategy.enums import ExecutionMode, OpportunityStatus
from core.modules.strategy.services.data import StrategyDataInjectionService

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
        self.stock_info = {"id": self.stock_id, "name": self.stock_id, "industry": "", "type": "", "exchange_center": ""}
        self.contract_cache = ContractCacheManager()
        self.data_manager = StrategyDataInjectionService(
            stock_id=self.stock_id,
            settings=self.settings,
            contract_cache=self.contract_cache,
            global_extra_cache=self.job_payload.get("global_extra_cache"),
        )
        self.opportunity_counter = 0
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
                "settings": self.settings.to_dict(),
            }
        )
        if hasattr(self.strategy_instance, "stock_info"):
            self.strategy_instance.stock_info = self.stock_info

    def run(self) -> Dict[str, Any]:
        self.profiler.start_timer("total")
        try:
            lookback_days = min(self.settings.min_required_records, MAX_LOOKBACK_DAYS)
            actual_start_date = self._get_date_before(self.start_date, lookback_days)
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
                    q_start = time.perf_counter()
                    self.data_manager.load_declared_items(extras, start_date=actual_start_date, end_date=self.end_date)
                    q_elapsed = time.perf_counter() - q_start
                    for _ in range(len(extras)):
                        self.profiler.record_db_query(q_elapsed / max(len(extras), 1))
                self.data_manager.rebuild_data_cursor()
            else:
                q_start = time.perf_counter()
                self.data_manager.load_historical_data(start_date=actual_start_date, end_date=self.end_date)
                q_elapsed = time.perf_counter() - q_start
                required_sources = getattr(self.settings, "required_data_sources", []) or []
                estimated = max(len(required_sources), 1)
                for _ in range(estimated):
                    self.profiler.record_db_query(q_elapsed / estimated)
            self.profiler.metrics.time_load_data = self.profiler.end_timer("load_data")

            all_klines = self.data_manager.get_klines()
            if not all_klines or len(all_klines) < self.settings.min_required_records:
                return {"success": True, "stock_id": self.stock_id, "opportunity_count": 0}

            tracker = {"stock_id": self.stock_id, "passed_dates": [], "active_opportunities": [], "all_opportunities": []}
            self.profiler.start_timer("enumerate")
            last_kline = None
            for current_kline in all_klines:
                virtual_date_of_today = current_kline["date"]
                tracker["passed_dates"].append(virtual_date_of_today)
                if len(tracker["passed_dates"]) < self.settings.min_required_records:
                    continue
                data_of_today = self.data_manager.get_data_until(virtual_date_of_today)
                self._enumerate_single_day(tracker, current_kline, data_of_today)
                last_kline = current_kline
            self.profiler.metrics.time_enumerate = self.profiler.end_timer("enumerate")
            if tracker["active_opportunities"] and last_kline:
                self._close_all_open_opportunities(tracker, last_kline)
            self.profiler.start_timer("serialize")
            opportunities_dict = [opp.to_dict() for opp in tracker["all_opportunities"]]
            self.profiler.metrics.time_serialize = self.profiler.end_timer("serialize")
            if self.job_payload.get("output_dir") and opportunities_dict:
                self.profiler.start_timer("save_csv")
                self._save_stock_results(self.job_payload["output_dir"], opportunities_dict)
                self.profiler.metrics.time_save_csv = self.profiler.end_timer("save_csv")
            self.profiler.metrics.kline_count = len(all_klines)
            self.profiler.metrics.opportunity_count = len(opportunities_dict)
            self.profiler.metrics.target_count = sum(len(opp.get("completed_targets", []) or []) for opp in opportunities_dict)
            self.profiler.metrics.time_total = self.profiler.end_timer("total")
            metrics = self.profiler.finalize()
            return {"success": True, "stock_id": self.stock_id, "opportunity_count": len(opportunities_dict), "performance_metrics": metrics.to_dict()}
        except Exception as exc:
            logger.error("enumeration failed: stock_id=%s, error=%s", self.stock_id, exc, exc_info=True)
            return {"success": False, "stock_id": self.stock_id, "opportunity_count": 0, "error": str(exc)}

    def _get_date_before(self, date_str: str, days: int) -> str:
        from datetime import datetime, timedelta

        try:
            return (datetime.strptime(date_str, "%Y%m%d") - timedelta(days=days)).strftime("%Y%m%d")
        except Exception:
            return date_str

    def _enumerate_single_day(self, tracker: Dict[str, Any], current_kline: Dict[str, Any], data_of_today: Dict[str, Any]):
        completed_indices = []
        for idx, opportunity in enumerate(tracker["active_opportunities"]):
            if opportunity.check_targets(current_kline=current_kline, goal_config=self.settings.goal):
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
        opportunity.trigger_price = current_kline["close"]
        opportunity.status = OpportunityStatus.ACTIVE.value
        opportunity.completed_targets = []
        self.opportunity_counter += 1
        opportunity.opportunity_id = str(self.opportunity_counter)
        opportunity.enrich_from_framework(strategy_name=self.strategy_name, strategy_version="1.0", opportunity_id=opportunity.opportunity_id)
        tracker["active_opportunities"].append(opportunity)
        tracker["all_opportunities"].append(opportunity)

    def _scan_opportunity_with_data(self, data: Dict[str, Any]):
        settings_dict = self.settings.to_dict()
        return self.strategy_instance.scan_opportunity(data, settings_dict)

    def _close_all_open_opportunities(self, tracker: Dict[str, Any], last_kline: Dict[str, Any]):
        for opportunity in tracker["active_opportunities"]:
            opportunity.settle(last_kline=last_kline, reason="enumeration_end")
        tracker["active_opportunities"].clear()

    def _save_stock_results(self, output_dir: str, opportunities: List[Dict[str, Any]]):
        import json
        from pathlib import Path

        from core.utils.io.csv_io import write_dicts_to_csv

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        opp_rows: List[Dict[str, Any]] = []
        target_rows: List[Dict[str, Any]] = []
        excluded_fields = {
            "completed_targets",
            "config_hash",
            "created_at",
            "updated_at",
            "record_of_today",
            "dynamic_loss_active",
            "dynamic_loss_highest",
            "expired_reason",
            "expired_date",
            "exit_reason",
            "protect_loss_active",
            "scan_date",
            "stock",
            "stock_id",
            "stock_name",
            "strategy_name",
            "strategy_version",
            "holding_days",
            "max_drawdown",
            "metadata",
            "price_return",
            "tracking",
            "triggered_stop_loss_idx",
        }
        for opp_dict in opportunities:
            completed_targets = opp_dict.get("completed_targets", [])
            for target in completed_targets or []:
                target_rows.append(
                    {
                        "opportunity_id": opp_dict.get("opportunity_id", ""),
                        "date": target.get("date", ""),
                        "sell_price": target.get("price", ""),
                        "sell_ratio": target.get("sell_ratio", ""),
                        "profit": target.get("profit", ""),
                        "weighted_profit": target.get("weighted_profit", ""),
                        "reason": target.get("reason", ""),
                        "roi": target.get("roi", ""),
                    }
                )
            opp_row = {k: v for k, v in opp_dict.items() if k not in excluded_fields}
            for key, value in opp_row.items():
                if isinstance(value, (dict, list)):
                    opp_row[key] = json.dumps(value, ensure_ascii=False)
                elif value is None:
                    opp_row[key] = ""
            opp_rows.append(opp_row)
        if opp_rows:
            write_dicts_to_csv(output_path / f"{self.stock_id}_opportunities.csv", opp_rows, preferred_order=list(opp_rows[0].keys()))
        if target_rows:
            write_dicts_to_csv(output_path / f"{self.stock_id}_targets.csv", target_rows, preferred_order=list(target_rows[0].keys()))


__all__ = ["OpportunityEnumeratorWorker"]
