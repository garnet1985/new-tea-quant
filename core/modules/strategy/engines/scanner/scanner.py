#!/usr/bin/env python3
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional
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
    from core.modules.strategy.engines.shared.data_classes.discovered_strategy import (
        DiscoveredStrategy,
    )


@dataclass
class Scanner:
    strategy_name: str
    data_manager: any
    is_verbose: bool = False
    strategy_info: Optional["DiscoveredStrategy"] = None

    def __post_init__(self):
        self._strategy_info = self.strategy_info or load_strategy_info(self.strategy_name)
        if self._strategy_info is None:
            raise ValueError(f"cannot load strategy: {self.strategy_name}")
        self.settings = StrategyScannerSettings.from_base_settings(self._strategy_info.settings)
        self.date_resolver = ScanDateResolver(self.data_manager)
        self.cache_manager = ScanCacheManager(self.strategy_name, self.settings.max_cache_days)
        self.adapter_dispatcher = AdapterDispatcher(self.strategy_name)

    def scan(
        self,
        *,
        force: bool = False,
        on_job_done: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        scan_date, stock_ids = self.date_resolver.resolve_scan_date(
            use_strict=self.settings.use_strict_previous_trading_day
        )
        self.cache_manager.cleanup_old_cache()

        cache_csv = self.cache_manager.cache_base_dir / scan_date / "opportunities.csv"
        use_cache = (not force) and cache_csv.is_file()

        if use_cache:
            opportunities = self.cache_manager.load_opportunities(scan_date)
            if callable(on_job_done):
                try:
                    on_job_done(
                        {
                            "progress_pct": 99,
                            "total_jobs": 1,
                            "completed_jobs": 1,
                            "failed_jobs": 0,
                            "cancelled_jobs": 0,
                            "last_job_id": "__cache__",
                            "last_job_status": "completed",
                        }
                    )
                except Exception:
                    logger.exception("[Scanner] on_job_done failed (cache fast-path)")
        else:
            opportunities = self._scan_stocks(scan_date, stock_ids, on_job_done=on_job_done)
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

    def _scan_stocks(
        self,
        scan_date: str,
        stock_ids: List[str],
        *,
        on_job_done: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> List[Opportunity]:
        from core.infra.worker.multi_process.process_worker import JobStatus
        from core.modules.strategy.services.execution.scanner_job_pipeline import (
            run_scanner_jobs_via_pipeline,
        )

        info = self._strategy_info
        market_profile_id = str(info.settings.market_profile.profile_id or "").strip()
        jobs = [
            {
                "stock_id": stock_id,
                "execution_mode": ExecutionMode.SCAN.value,
                "strategy_name": self.strategy_name,
                "settings": info.settings.to_dict(),
                "market_profile_id": market_profile_id,
                "scan_date": scan_date,
                "worker_module_path": info.worker_module_path,
                "worker_class_name": info.worker_class_name,
            }
            for stock_id in stock_ids
        ]
        if not jobs:
            return []

        job_results = run_scanner_jobs_via_pipeline(
            stock_jobs=jobs,
            max_workers=self.settings.max_workers,
            total_jobs=len(jobs),
            run_name=f"scanner:{self.strategy_name}",
            on_job_progress=on_job_done if callable(on_job_done) else None,
        )
        opportunities: List[Opportunity] = []
        for job_result in job_results:
            if job_result.status != JobStatus.COMPLETED or not job_result.result:
                continue
            result = job_result.result
            if result.get("success") and result.get("opportunity"):
                opportunities.append(Opportunity.from_dict(result["opportunity"]))
        return opportunities

    @staticmethod
    def _execute_single_job(payload: Dict[str, Any]) -> Dict[str, Any]:
        """扫描并行请走 ``run_scanner_jobs_via_pipeline``。"""
        from core.modules.strategy.services.execution.scanner_job_pipeline import (
            run_scanner_worker_payload,
        )

        return run_scanner_worker_payload(payload)

    def _calculate_summary(self, opportunities: List[Opportunity]) -> Dict[str, Any]:
        if not opportunities:
            return {
                "total_opportunities": 0,
                "total_stocks": 0,
                "stocks_with_opportunities": [],
                "at_limit_up_count": 0,
            }
        stocks_with_opps = {opp.stock_id for opp in opportunities}
        at_limit_up = sum(1 for opp in opportunities if opp.buy_at_limit_up is True)
        return {
            "total_opportunities": len(opportunities),
            "total_stocks": len(stocks_with_opps),
            "stocks_with_opportunities": list(stocks_with_opps),
            "at_limit_up_count": at_limit_up,
        }


__all__ = ["Scanner"]
