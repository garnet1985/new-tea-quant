"""Scanner Pipeline — 扫描领域编排（多策略入口 + 单策略执行）。

本文件:
- ScannerPipeline.scan: 解析目标策略、demo/严格门闸、逐策略执行
- ScannerPipeline.run: 单策略（日期 → cache/BE → adapters）
  边界: 负责 scan 领域端到端；不负责 simulate 指纹或 Facade 公开 API 形状以外的编排
"""
from __future__ import annotations

import logging
from dataclasses import fields as dc_fields
from typing import Any, Callable, Dict, List, Optional

from core.infra.job_pipeline.profile import (
    WorkerProfiles,
    resolve_entity_based_performance_for_profile,
)
from core.modules.backtest_engine import BacktestEngine
from core.modules.data_manager import DataManager
from core.modules.strategy.core.engines.scanner.executor import ScannerJobExecutor
from core.modules.strategy.core.engines.scanner.helpers import (
    AdapterDispatcher,
    ScanCacheManager,
    ScanDateResolver,
    opportunity_enter_at_limit,
)
from core.modules.strategy.core.engines.scanner.job_builder import ScannerJobBuilder
from core.modules.strategy.core.engines.shared.data_class.opportunity import Opportunity
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.services.discovery import DiscoveryService
from core.modules.strategy.core.services.discovery.data.discovered_strategy import (
    EnabledStrategyInfo,
)

logger = logging.getLogger(__name__)


class ScannerPipeline:
    """扫描领域编排入口。"""

    @classmethod
    def scan(
        cls,
        key_or_id: Optional[str] = None,
        *,
        demo: bool = False,
        force: bool = False,
        on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
        data_manager: Any = None,
    ) -> Dict[str, Any]:
        """多策略扫描入口（含目标解析与严格交易日门闸）。

        未指定 ``key_or_id`` 时扫描全部已启用策略；显式指定时即使未启用也扫。
        ``demo=True`` 关闭严格交易日并跳过锚点 vs K 线对齐门闸。
        """
        targets = cls.resolve_targets(key_or_id)
        if not targets:
            return {}

        dm = data_manager if data_manager is not None else DataManager()
        kline_latest = ScanDateResolver.load_kline_latest_date(dm)
        if not kline_latest:
            logger.error("无法解析 K 线最新日期（sys_stock_klines 可能为空）")
            return {}

        results: Dict[str, Any] = {}
        for info in targets:
            name = str(info.key or info.unique_relative_path or "").strip()
            settings = StrategySettings.from_dict(dict(info.settings or {}))
            settings.apply_defaults()
            if demo:
                settings.scanner.set_use_strict_previous_trading_day(False)

            if not demo and not cls._passes_strict_anchor_gate(
                dm, settings=settings, kline_latest=kline_latest, strategy_name=name
            ):
                continue

            try:
                results[name] = cls.run(
                    info,
                    settings,
                    force=force,
                    on_progress=on_progress,
                    data_manager=dm,
                )
            except Exception as exc:
                logger.error("扫描失败 strategy=%s error=%s", name, exc, exc_info=True)
        return results

    @classmethod
    def resolve_targets(
        cls,
        key_or_id: Optional[str],
    ) -> List[EnabledStrategyInfo]:
        """显式名 → 单策略（未启用也允许）；未指定 → 全部启用。"""
        needle = str(key_or_id or "").strip()
        field_names = {f.name for f in dc_fields(EnabledStrategyInfo) if f.init}

        def _as_enabled(info: Any) -> EnabledStrategyInfo:
            if isinstance(info, EnabledStrategyInfo):
                return info
            kwargs = {k: v for k, v in info.__dict__.items() if k in field_names}
            return EnabledStrategyInfo(**kwargs)

        if needle:
            for info in DiscoveryService.discover_strategies():
                if info.key == needle or info.id() == needle:
                    if not info.is_enabled:
                        logger.warning("策略未启用，仍将扫描: %s", needle)
                    return [_as_enabled(info)]
            logger.error("策略不存在: %s", needle)
            return []

        enabled = DiscoveryService.get_enabled_strategies()
        if not enabled:
            logger.warning("没有可扫描的策略")
        return sorted(enabled, key=lambda x: str(x.key or x.unique_relative_path or ""))

    @staticmethod
    def _passes_strict_anchor_gate(
        data_manager: Any,
        *,
        settings: StrategySettings,
        kline_latest: str,
        strategy_name: str,
    ) -> bool:
        """非 demo：锚点须与库内 K 线最新日一致，否则跳过该策略。"""
        anchor = ScanDateResolver.resolve_anchor_date(
            data_manager,
            use_strict=settings.scanner.use_strict_previous_trading_day,
        )
        if anchor and anchor != kline_latest:
            logger.warning(
                "跳过扫描 %s：锚点 %s ≠ K 线最新 %s（demo=True 可放宽）",
                strategy_name,
                anchor,
                kline_latest,
            )
            return False
        return True

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
        """单策略扫描（日期 → cache / BE → adapters）。"""
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
        jobs = ScannerJobBuilder.build_jobs(
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
            callbacks=ScannerJobExecutor.build_run_callbacks(),
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
            1 for opp in opportunities if opportunity_enter_at_limit(opp) is True
        )
        return {
            "total_opportunities": len(opportunities),
            "total_stocks": len(stocks),
            "stocks_with_opportunities": sorted(stocks),
            "at_limit_up_count": at_limit,
        }


__all__ = ["ScannerPipeline"]
