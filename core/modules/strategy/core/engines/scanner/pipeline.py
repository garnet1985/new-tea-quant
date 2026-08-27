"""Scanner Pipeline — 扫描领域编排。

- ``scan``：CLI / 多策略
- ``run``：单策略（日期 → cache/BE → ReportManager）
- ``page_context`` / ``readiness`` / ``block_reason``：工作台读模型（能否扫、已有落盘）

进度文件由 Facade ``Strategy.scan_run`` 写；本类不碰 ``ScanProgress`` 生命周期。
"""
from __future__ import annotations

import logging
from dataclasses import fields as dc_fields
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

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
        block = cls.block_reason(demo=demo, data_manager=dm)
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
            cls.apply_scan_mode(settings, demo=bool(demo))

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
    def strategy_key(info: EnabledStrategyInfo, fallback: str = "") -> str:
        return str(info.key or info.unique_relative_path or fallback or "").strip()

    @staticmethod
    def strategy_folder(info: EnabledStrategyInfo):
        from core.infra.project_context import ProjectContext

        resolved = getattr(info, "resolved_folder", None)
        if callable(resolved):
            return resolved()
        if getattr(info, "folder", None) is not None:
            return Path(info.folder)
        return ProjectContext.path.coerce_strategy_folder(
            getattr(info, "unique_relative_path", None) or getattr(info, "key", None) or ""
        )

    @classmethod
    def apply_scan_mode(cls, settings: StrategySettings, *, demo: bool) -> bool:
        """``demo=False`` 强制严格交易日；返回是否严格模式。"""
        if demo:
            settings.scanner.set_use_strict_previous_trading_day(False)
            return False
        settings.scanner.set_use_strict_previous_trading_day(True)
        return True

    @classmethod
    def block_reason(cls, *, demo: bool, data_manager: Any = None) -> str:
        """非 demo 时返回数据门禁文案；demo 或已就绪返回空串。"""
        if demo:
            return ""
        dm = data_manager if data_manager is not None else DataManager(is_verbose=False)
        return ScanDateResolver.strict_data_block_reason(dm)

    @classmethod
    def page_context(cls) -> Dict[str, Any]:
        from core.modules.data_source import DataSourceManager

        data_end: Dict[str, Any] = {}
        demo_scan_cutoff_date = ""
        try:
            data_mgr = DataManager(is_verbose=False)
            data_mgr.initialize()
            data_end = DataSourceManager.get_data_end_meta(data_mgr)
            demo_scan_cutoff_date = ScanDateResolver.resolve_anchor_date(
                data_mgr,
                use_strict=False,
            )
        except Exception:
            logger.debug("scanner page_context failed", exc_info=True)
        return {
            "data_end": data_end,
            "demo_scan_cutoff_date": demo_scan_cutoff_date or None,
        }

    @classmethod
    def resolve_one(
        cls, key_or_id: str
    ) -> Tuple[Optional[EnabledStrategyInfo], Optional[str]]:
        name = str(key_or_id or "").strip()
        if not name:
            return None, "strategy_name 无效"
        targets = cls.resolve_targets(name)
        if not targets:
            return None, "策略不存在或无法加载"
        return targets[0], None

    @classmethod
    def readiness(cls, key_or_id: str, *, demo: bool = False) -> Dict[str, Any]:
        """工作台：能否开扫 + 已有落盘摘要。"""
        from core.modules.strategy.core.services.progress.scan_progress import (
            ScanProgress,
        )

        name = str(key_or_id or "").strip()
        if not name:
            return {"primary_action": "run", "can_scan": False, "block_reason": "strategy_name 无效"}
        try:
            info, err = cls.resolve_one(name)
            if err or info is None:
                return {
                    "primary_action": "run",
                    "can_scan": False,
                    "block_reason": err or "策略不存在或无法加载",
                }

            folder = cls.strategy_folder(info)
            data_mgr = DataManager(is_verbose=False)
            settings = StrategySettings.from_dict(dict(info.settings or {}))
            settings.apply_defaults()
            use_strict = cls.apply_scan_mode(settings, demo=bool(demo))

            block = cls.block_reason(demo=bool(demo), data_manager=data_mgr)
            if block:
                kline_latest = ScanDateResolver.load_kline_latest_date(data_mgr)
                report = None
                primary = "run"
                if kline_latest:
                    cache = ScanCacheManager(folder, settings.scanner.max_cache_days)
                    summary_payload = cache.load_scan_summary(kline_latest)
                    if isinstance(summary_payload, dict):
                        opportunities = cache.load_opportunities(kline_latest)
                        total_opps = int(summary_payload.get("total_opportunities") or 0)
                        report = {
                            "date": str(summary_payload.get("date") or kline_latest),
                            "total_opportunities": total_opps,
                            "total_stocks": int(summary_payload.get("total_stocks") or 0),
                            "summary": summary_payload.get("summary")
                            if isinstance(summary_payload.get("summary"), dict)
                            else {
                                "total_opportunities": total_opps,
                                "total_stocks": 0,
                                "stocks_with_opportunities": [],
                            },
                            "opportunities": ScanProgress.opportunity_rows(opportunities),
                        }
                        primary = "rerun"
                return {
                    "primary_action": primary,
                    "can_scan": False,
                    "block_reason": block,
                    **({"report": report} if report else {}),
                }

            resolver = ScanDateResolver(data_mgr)
            scan_date, stock_ids = resolver.resolve_scan_date(use_strict=use_strict)
            cache = ScanCacheManager(folder, settings.scanner.max_cache_days)
            summary_payload = cache.load_scan_summary(scan_date)
            if not isinstance(summary_payload, dict):
                return {"primary_action": "run", "can_scan": True, "block_reason": ""}

            opportunities = cache.load_opportunities(scan_date)
            total_from_summary = summary_payload.get("total_opportunities")
            try:
                total_opps = (
                    int(total_from_summary)
                    if total_from_summary is not None
                    else len(opportunities)
                )
            except (TypeError, ValueError):
                total_opps = len(opportunities)
            stocks_with_opps = (
                {o.stock_id for o in opportunities} if opportunities else set()
            )
            summary = {
                "total_opportunities": total_opps,
                "total_stocks": len(stocks_with_opps),
                "stocks_with_opportunities": sorted(stocks_with_opps),
            }
            if isinstance(summary_payload.get("summary"), dict):
                merged = dict(summary_payload.get("summary") or {})
                merged.update(summary)
                summary = merged
            total_stocks = summary_payload.get("total_stocks")
            try:
                total_stocks_n = (
                    int(total_stocks) if total_stocks is not None else len(stock_ids)
                )
            except (TypeError, ValueError):
                total_stocks_n = len(stock_ids)
            report: Dict[str, Any] = {
                "date": str(summary_payload.get("date") or scan_date),
                "total_opportunities": total_opps,
                "total_stocks": total_stocks_n,
                "summary": summary,
                "opportunities": ScanProgress.opportunity_rows(opportunities),
            }
            return {
                "primary_action": "rerun",
                "can_scan": True,
                "block_reason": "",
                "report": report,
            }
        except Exception:
            logger.debug("scanner readiness failed strategy=%s", name, exc_info=True)
            return {
                "primary_action": "run",
                "can_scan": False,
                "block_reason": "读取扫描就绪状态失败",
            }

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
        strategy_key = cls.strategy_key(strategy_info)
        strategy_folder = cls.strategy_folder(strategy_info)

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

        # 横截面策略：先 asof 选股再扫，避免 has_opportunity 对全宇宙放行
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
