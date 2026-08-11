"""Scanner Pipeline — 扫描领域编排（多策略入口 + 单策略执行）。

本文件:
- ScannerPipeline.scan: 解析目标策略、demo/严格门闸、逐策略执行
- ScannerPipeline.run: 单策略（日期 → cache/BE → ReportManager）
  边界: 负责 scan 领域端到端；不负责 simulate 指纹或 Facade 公开 API 形状以外的编排
"""
from __future__ import annotations

import logging
from dataclasses import fields as dc_fields
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from core.modules.backtest_engine import BacktestEngine
from core.modules.data_manager import DataManager
from core.modules.strategy.core.engines.scanner.executor import ScannerJobExecutor
from core.modules.strategy.core.engines.scanner.helpers import (
    ScanCacheManager,
    ScanDateResolver,
    ScannerCalendarAsof,
)
from core.modules.strategy.core.engines.scanner.job_builder import ScannerJobBuilder
from core.modules.strategy.core.engines.scanner.report_manager import ReportManager
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
        if not demo:
            block = ScanDateResolver.strict_data_block_reason(dm)
            if block:
                raise ValueError(block)

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
            else:
                # 与 UI/API 严格模式一致：强制真实交易日对齐
                settings.scanner.set_use_strict_previous_trading_day(True)

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
        """单策略扫描（日期 → cache / BE → ReportManager）。"""
        from core.infra.project_context import ProjectContext

        settings.apply_defaults()
        dm = data_manager if data_manager is not None else DataManager()
        strategy_key = str(
            strategy_info.key or strategy_info.unique_relative_path or ""
        ).strip()
        resolved = getattr(strategy_info, "resolved_folder", None)
        if callable(resolved):
            strategy_folder = resolved()
        elif getattr(strategy_info, "folder", None) is not None:
            strategy_folder = Path(strategy_info.folder)
        else:
            strategy_folder = ProjectContext.path.coerce_strategy_folder(
                strategy_info.unique_relative_path or strategy_key
            )

        resolver = ScanDateResolver(dm)
        use_strict = settings.scanner.use_strict_previous_trading_day
        scan_date, stock_ids, date_meta = resolver.resolve_scan_date_with_meta(
            use_strict=use_strict
        )

        scan_max = ProjectContext.config.get_scan_results_max_versions()
        cache = ScanCacheManager(
            strategy_folder,
            max_cache_days=scan_max,
        )
        cache.cleanup_old_cache()

        summary_path = cache.scan_summary_path(scan_date)
        use_cache = (not force) and summary_path.is_file()

        # 横截面策略：先 asof 选股再扫，避免 scan_opportunity 对全宇宙放行
        if not use_cache:
            stock_ids = ScannerCalendarAsof.filter_stock_ids(
                strategy_info=strategy_info,
                settings=settings,
                stock_ids=stock_ids,
                scan_date=scan_date,
                data_manager=dm,
            )

        report = ReportManager.begin(
            strategy_key=strategy_key,
            strategy_folder=strategy_folder,
            scan_date=scan_date,
            stock_ids=stock_ids,
            date_meta=date_meta,
            adapter_names=list(settings.scanner.adapter_names or []),
            max_cache_days=scan_max,
            skip_save=use_cache,
        )

        if use_cache:
            report.collect(cache.load_opportunities(scan_date))
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
            run_result = cls._run_backtest(
                strategy_info=strategy_info,
                settings=settings,
                stock_ids=stock_ids,
                scan_date=scan_date,
                on_progress=on_progress,
            )
            report.collect(run_result)

        return report.finalize(present=True)

    @classmethod
    def _run_backtest(
        cls,
        *,
        strategy_info: EnabledStrategyInfo,
        settings: StrategySettings,
        stock_ids: List[str],
        scan_date: str,
        on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> Any:
        jobs = ScannerJobBuilder.build_jobs(
            strategy_info=strategy_info,
            settings=settings,
            stock_ids=stock_ids,
            scan_date=scan_date,
        )
        if not jobs:
            return None

        performance = BacktestEngine.Performance.resolve_entity_based_for_profile(
            BacktestEngine.Performance.Profiles.SCANNER
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

        return run_result


__all__ = ["ScannerPipeline"]
