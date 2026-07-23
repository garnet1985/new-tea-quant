"""Scanner Pipeline — 日期解析 → cache / BE 扫描 → adapters。"""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from core.infra.job_pipeline.profile import (
    WorkerProfiles,
    resolve_entity_based_performance_for_profile,
)
from core.modules.backtest_engine import BacktestEngine
from core.modules.data_manager import DataManager
from core.modules.strategy.core.engines.scanner.executor import JobExecutor
from core.modules.strategy.core.engines.scanner.helpers import (
    AdapterDispatcher,
    ScanCacheManager,
    ScanDateResolver,
    opportunity_buy_at_limit_up,
)
from core.modules.strategy.core.engines.scanner.job_builder import JobBuilder
from core.modules.strategy.core.engines.shared.data_class.opportunity import Opportunity
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.services.discovery.data.discovered_strategy import (
    EnabledStrategyInfo,
)

logger = logging.getLogger(__name__)


class ScannerPipeline:
    """单策略扫描编排入口。"""

    @classmethod
    def run(
        cls,
        strategy_info: EnabledStrategyInfo,
        settings: StrategySettings,
        *,
        force: bool = False,
        on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
        data_manager: Any = None,
    ) -> Dict[str, Any]:
        settings.apply_defaults()
        dm = data_manager if data_manager is not None else DataManager()
        strategy_key = str(
            strategy_info.key or strategy_info.unique_relative_path or ""
        ).strip()

        resolver = ScanDateResolver(dm)
        use_strict = settings.scanner.use_strict_previous_trading_day
        scan_date, stock_ids, date_meta = resolver.resolve_scan_date_with_meta(
            use_strict=use_strict
        )

        cache = ScanCacheManager(
            strategy_key,
            max_cache_days=settings.scanner.max_cache_days,
        )
        cache.cleanup_old_cache()

        csv_path = cache.opportunities_csv_path(scan_date)
        use_cache = (not force) and csv_path.is_file()

        if use_cache:
            opportunities = cache.load_opportunities(scan_date)
            if callable(on_progress):
                try:
                    on_progress(
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
                    logger.exception("scanner on_progress failed (cache)")
        else:
            opportunities = cls._scan_stocks(
                strategy_info=strategy_info,
                settings=settings,
                stock_ids=stock_ids,
                scan_date=scan_date,
                on_progress=on_progress,
            )
            if opportunities:
                cache.save_opportunities(scan_date, opportunities)

        summary = cls.calculate_summary(opportunities)
        AdapterDispatcher(strategy_key).dispatch(
            adapter_names=settings.scanner.adapter_names,
            opportunities=opportunities,
            context={
                "date": scan_date,
                "strategy_name": strategy_key,
                "scan_summary": summary,
                "date_meta": date_meta,
            },
        )
        return {
            "date": scan_date,
            "total_opportunities": len(opportunities),
            "total_stocks": len(stock_ids),
            "summary": summary,
            "date_meta": date_meta,
        }

    @classmethod
    def _scan_stocks(
        cls,
        *,
        strategy_info: EnabledStrategyInfo,
        settings: StrategySettings,
        stock_ids: List[str],
        scan_date: str,
        on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> List[Opportunity]:
        jobs = JobBuilder.build_jobs(
            strategy_info=strategy_info,
            settings=settings,
            stock_ids=stock_ids,
            scan_date=scan_date,
        )
        if not jobs:
            return []

        performance = resolve_entity_based_performance_for_profile(
            WorkerProfiles.SCANNER
        )
        run_result = BacktestEngine.entity_based.run(
            jobs=jobs,
            start=scan_date,
            end=scan_date,
            performance=performance,
            callbacks=JobExecutor.build_run_callbacks(),
            task_name=f"scanner_{strategy_info.key or 'run'}",
        )

        if callable(on_progress) and run_result is not None:
            try:
                on_progress(
                    {
                        "progress_pct": 100,
                        "total_jobs": int(getattr(run_result, "total_jobs", 0) or 0),
                        "completed_jobs": int(
                            getattr(run_result, "completed_jobs", 0) or 0
                        ),
                        "failed_jobs": int(getattr(run_result, "failed_jobs", 0) or 0),
                        "cancelled_jobs": 0,
                        "last_job_status": "completed",
                    }
                )
            except Exception:
                logger.exception("scanner on_progress failed")

        return cls._collect_opportunities(run_result)

    @staticmethod
    def _collect_opportunities(run_result: Any) -> List[Opportunity]:
        if run_result is None:
            return []
        out: List[Opportunity] = []
        for report in list(getattr(run_result, "job_results", None) or []):
            if not getattr(report, "success", False):
                continue
            data = report.data if isinstance(report.data, dict) else {}
            rows = data.get("opportunities") or []
            if not isinstance(rows, list):
                continue
            for row in rows:
                if isinstance(row, dict):
                    out.append(Opportunity.from_dict(row))
        return out

    @staticmethod
    def calculate_summary(opportunities: List[Opportunity]) -> Dict[str, Any]:
        if not opportunities:
            return {
                "total_opportunities": 0,
                "total_stocks": 0,
                "stocks_with_opportunities": [],
                "at_limit_up_count": 0,
            }
        stocks = {opp.stock_id for opp in opportunities if opp.stock_id}
        at_limit = sum(
            1 for opp in opportunities if opportunity_buy_at_limit_up(opp) is True
        )
        return {
            "total_opportunities": len(opportunities),
            "total_stocks": len(stocks),
            "stocks_with_opportunities": sorted(stocks),
            "at_limit_up_count": at_limit,
        }


__all__ = ["ScannerPipeline"]
