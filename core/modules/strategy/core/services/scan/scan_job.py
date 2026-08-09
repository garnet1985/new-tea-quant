"""Strategy scanner job execution (domain; no HTTP / no thread).

BFF owns async submit + single-flight; this module runs ``ScannerPipeline``
and drives ``ScanProgress`` disk updates.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from core.infra.project_context import ProjectContext
from core.modules.data_manager import DataManager
from core.modules.strategy.core.engines.scanner.helpers import (
    ScanCacheManager,
    ScanDateResolver,
)
from core.modules.strategy.core.engines.scanner.pipeline import ScannerPipeline
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.services.discovery.data.discovered_strategy import (
    EnabledStrategyInfo,
)
from core.modules.strategy.core.services.progress.scan_progress import ScanProgress

logger = logging.getLogger(__name__)


class ScanJob:
    """Resolve strategy, readiness helpers, and execute one scanner run."""

    @staticmethod
    def strategy_cache_key(info: EnabledStrategyInfo, fallback: str = "") -> str:
        """Stable id for progress / UI (not the on-disk strategy root)."""
        return str(info.unique_relative_path or info.key or fallback or "").strip()

    @staticmethod
    def strategy_folder(info: EnabledStrategyInfo):
        from pathlib import Path

        from core.infra.project_context import ProjectContext

        resolved = getattr(info, "resolved_folder", None)
        if callable(resolved):
            return resolved()
        if getattr(info, "folder", None) is not None:
            return Path(info.folder)
        return ProjectContext.path.coerce_strategy_folder(
            getattr(info, "unique_relative_path", None)
            or getattr(info, "key", None)
            or ""
        )

    @classmethod
    def resolve_strategy(
        cls, strategy_name: str
    ) -> Tuple[Optional[EnabledStrategyInfo], Optional[str]]:
        name = str(strategy_name or "").strip()
        if not name:
            return None, "strategy_name 无效"
        targets = ScannerPipeline.resolve_targets(name)
        if not targets:
            return None, "策略不存在或无法加载"
        return targets[0], None

    @classmethod
    def page_context(cls) -> Dict[str, Any]:
        from core.modules.data_source.core.catalog.freshness_probe import get_data_end_meta

        data_end: Dict[str, Any] = {}
        demo_scan_cutoff_date = ""
        try:
            data_mgr = DataManager(is_verbose=False)
            data_mgr.initialize()
            data_end = get_data_end_meta(data_mgr)
            demo_scan_cutoff_date = ScanDateResolver.resolve_anchor_date(
                data_mgr,
                use_strict=False,
            )
        except Exception:
            logger.debug("ScanJob.page_context failed", exc_info=True)
        return {
            "data_end": data_end,
            "demo_scan_cutoff_date": demo_scan_cutoff_date or None,
        }

    @classmethod
    def readiness(cls, *, strategy_name: str, demo: bool = False) -> Dict[str, Any]:
        name = str(strategy_name or "").strip()
        if not name:
            return {"primary_action": "run"}
        try:
            info, err = cls.resolve_strategy(name)
            if err or info is None:
                return {"primary_action": "run"}

            path_key = cls.strategy_cache_key(info, name)
            folder = cls.strategy_folder(info)
            data_mgr = DataManager(is_verbose=False)
            kline_latest = ScanDateResolver.load_kline_latest_date(data_mgr)
            if not kline_latest:
                return {"primary_action": "run"}

            settings = StrategySettings.from_dict(dict(info.settings or {}))
            settings.apply_defaults()
            use_strict = bool(settings.scanner.use_strict_previous_trading_day)
            if demo:
                use_strict = False
            if not demo:
                cal_latest = ScanDateResolver.resolve_anchor_date(
                    data_mgr, use_strict=use_strict
                )
                if not cal_latest or cal_latest != kline_latest:
                    return {"primary_action": "run"}

            resolver = ScanDateResolver(data_mgr)
            scan_date, stock_ids = resolver.resolve_scan_date(use_strict=use_strict)
            csv_path = (
                ProjectContext.path.get_strategy_scan_results_directory(folder)
                / scan_date
                / "opportunities.csv"
            )
            if not csv_path.is_file():
                return {"primary_action": "run"}

            cache = ScanCacheManager(folder, settings.scanner.max_cache_days)
            opportunities = cache.load_opportunities(scan_date)
            stocks_with_opps = (
                {o.stock_id for o in opportunities} if opportunities else set()
            )
            summary = {
                "total_opportunities": len(opportunities),
                "total_stocks": len(stocks_with_opps),
                "stocks_with_opportunities": sorted(stocks_with_opps),
            }
            report: Dict[str, Any] = {
                "date": scan_date,
                "total_opportunities": len(opportunities),
                "total_stocks": len(stock_ids),
                "summary": summary,
                "opportunities": ScanProgress.opportunity_rows(opportunities),
            }
            return {"primary_action": "rerun", "report": report}
        except Exception:
            logger.debug("ScanJob.readiness failed strategy=%s", name, exc_info=True)
            return {"primary_action": "run"}

    @classmethod
    def execute(
        cls,
        *,
        strategy_name: str,
        job_id: str,
        demo: bool = False,
        force: bool = False,
    ) -> None:
        """Run scanner for an already-seeded job_id; updates ``ScanProgress``."""
        name = str(strategy_name or "").strip()
        jid = str(job_id or "").strip()
        prog = ScanProgress.for_job(name, jid)
        prog.mark_running()
        try:
            info, err = cls.resolve_strategy(name)
            if err or info is None:
                raise ValueError(err or "无法解析策略")

            path_key = cls.strategy_cache_key(info, name)
            folder = cls.strategy_folder(info)
            data_mgr = DataManager(is_verbose=False)

            kline_latest = ScanDateResolver.load_kline_latest_date(data_mgr)
            if not kline_latest:
                raise ValueError("无法解析 K 线最新日期（sys_stock_klines 可能为空）")

            settings = StrategySettings.from_dict(dict(info.settings or {}))
            settings.apply_defaults()
            use_strict = bool(settings.scanner.use_strict_previous_trading_day)
            if demo:
                settings.scanner.set_use_strict_previous_trading_day(False)
                use_strict = False

            if not demo:
                cal_latest = ScanDateResolver.resolve_anchor_date(
                    data_mgr, use_strict=use_strict
                )
                if not cal_latest:
                    raise ValueError("无法解析最新已完成交易日（日历服务不可用）")
                if cal_latest != kline_latest:
                    raise ValueError(
                        f"数据未对齐最新交易日：anchor={cal_latest}，kline={kline_latest} "
                        f"(strict={use_strict})"
                    )

            def _on_progress(payload: Dict[str, Any]) -> None:
                prog.tick(payload)

            report = ScannerPipeline.run(
                info,
                settings,
                force=bool(force),
                on_progress=_on_progress,
                data_manager=data_mgr,
            )
            if isinstance(report, dict):
                report.setdefault("strategy_key", path_key)
            prog.complete(
                report if isinstance(report, dict) else {},
                cache_key=str(folder),
            )
        except Exception as exc:
            logger.exception(
                "Scanner run failed job_id=%s strategy=%s", jid, name
            )
            prog.fail(str(exc))
            raise


__all__ = ["ScanJob"]
