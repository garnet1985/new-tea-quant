#!/usr/bin/env python3
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional
import logging

from core.modules.strategy.engines.scanner.data_classes.settings import StrategyScannerSettings
from core.modules.strategy.engines.scanner.helpers import (
    AdapterDispatcher,
    ScanCacheManager,
    ScanDateResolver,
)
from core.modules.strategy.engines.shared.data_classes.opportunity import Opportunity
from core.modules.strategy.enums import ExecutionMode
from core.modules.strategy.engines.shared.helpers.strategy_runtime import load_strategy_info

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from core.modules.strategy.engines.shared.data_classes.strategy_info import StrategyInfo


@dataclass
class Scanner:
    strategy_name: str
    data_manager: any
    is_verbose: bool = False
    strategy_info: Optional["StrategyInfo"] = None

    def __post_init__(self):
        self._strategy_info = self.strategy_info or load_strategy_info(self.strategy_name)
        if self._strategy_info is None:
            raise ValueError(f"cannot load strategy: {self.strategy_name}")
        self.settings = StrategyScannerSettings.from_base_settings(self._strategy_info.settings)
        self.date_resolver = ScanDateResolver(self.data_manager)
        self.cache_manager = ScanCacheManager(self.strategy_name, self.settings.max_cache_days)
        self.adapter_dispatcher = AdapterDispatcher(self.strategy_name)

    def scan(self) -> Dict[str, Any]:
        scan_date, stock_ids = self.date_resolver.resolve_scan_date(
            use_strict=self.settings.use_strict_previous_trading_day
        )
        self.cache_manager.cleanup_old_cache()
        opportunities = self._scan_stocks(scan_date, stock_ids)
        if opportunities:
            self.cache_manager.save_opportunities(scan_date, opportunities)
        summary = self._calculate_summary(opportunities)
        self.adapter_dispatcher.dispatch(
            adapter_names=self.settings.adapter_names,
            opportunities=opportunities,
            context={"date": scan_date, "strategy_name": self.strategy_name, "scan_summary": summary},
        )
        return {
            "date": scan_date,
            "total_opportunities": len(opportunities),
            "total_stocks": len(stock_ids),
            "summary": summary,
        }

    def _scan_stocks(self, scan_date: str, stock_ids: List[str]) -> List[Opportunity]:
        from core.infra.worker.multi_process.process_worker import ExecutionMode as ProcessExecutionMode
        from core.infra.worker.multi_process.process_worker import ProcessWorker

        info = self._strategy_info
        jobs = [
            {
                "stock_id": stock_id,
                "execution_mode": ExecutionMode.SCAN.value,
                "strategy_name": self.strategy_name,
                "settings": info.settings.to_dict(),
                "scan_date": scan_date,
                "worker_module_path": info.worker_module_path,
                "worker_class_name": info.worker_class_name,
            }
            for stock_id in stock_ids
        ]
        worker_pool = ProcessWorker(
            max_workers=ProcessWorker.resolve_max_workers(self.settings.max_workers, module_name="Scanner"),
            execution_mode=ProcessExecutionMode.QUEUE,
            job_executor=Scanner._execute_single_job,
            is_verbose=self.is_verbose,
        )
        worker_pool.run_jobs([{"id": job["stock_id"], "payload": job} for job in jobs])
        opportunities: List[Opportunity] = []
        for job_result in worker_pool.get_results():
            if job_result.status.value == "completed":
                result = job_result.result
                if result.get("success") and result.get("opportunity"):
                    opportunities.append(Opportunity.from_dict(result["opportunity"]))
        return opportunities

    @staticmethod
    def _execute_single_job(payload: Dict[str, Any]) -> Dict[str, Any]:
        import importlib

        stock_id = payload["stock_id"]
        try:
            worker_module = importlib.import_module(payload["worker_module_path"])
            worker_class = getattr(worker_module, payload["worker_class_name"])
            return worker_class(payload).run()
        except Exception as exc:
            logger.error("[Scanner] stock scan failed: %s - %s", stock_id, exc, exc_info=True)
            return {"success": False, "stock_id": stock_id, "opportunity": None, "error": str(exc)}

    def _calculate_summary(self, opportunities: List[Opportunity]) -> Dict[str, Any]:
        if not opportunities:
            return {"total_opportunities": 0, "total_stocks": 0, "stocks_with_opportunities": []}
        stocks_with_opps = set([opp.stock_id for opp in opportunities])
        return {
            "total_opportunities": len(opportunities),
            "total_stocks": len(stocks_with_opps),
            "stocks_with_opportunities": list(stocks_with_opps),
        }


__all__ = ["Scanner"]
