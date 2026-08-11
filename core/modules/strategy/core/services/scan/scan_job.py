"""Strategy scanner job execution (domain; no HTTP / no thread).

BFF owns async submit + single-flight; this module runs ``ScannerPipeline``
and drives ``ScanProgress`` disk updates.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

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
            logger.debug("ScanJob.page_context failed", exc_info=True)
        return {
            "data_end": data_end,
            "demo_scan_cutoff_date": demo_scan_cutoff_date or None,
        }

    @classmethod
    def apply_scan_mode(cls, settings: StrategySettings, *, demo: bool) -> bool:
        """UI/API 模式落到 settings：``demo=False`` 强制严格交易日门禁。

        返回是否严格模式（``use_strict``）。
        """
        if demo:
            settings.scanner.set_use_strict_previous_trading_day(False)
            return False
        settings.scanner.set_use_strict_previous_trading_day(True)
        return True

    @classmethod
    def strict_block_reason(
        cls,
        *,
        demo: bool,
        data_manager: Any = None,
    ) -> str:
        """非 demo（严格）时返回阻断文案；demo 或已就绪返回空串。"""
        if demo:
            return ""
        dm = data_manager if data_manager is not None else DataManager(is_verbose=False)
        return ScanDateResolver.strict_data_block_reason(dm)

    @classmethod
    def readiness(cls, *, strategy_name: str, demo: bool = False) -> Dict[str, Any]:
        name = str(strategy_name or "").strip()
        if not name:
            return {"primary_action": "run", "can_scan": False, "block_reason": "strategy_name 无效"}
        try:
            info, err = cls.resolve_strategy(name)
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

            block = cls.strict_block_reason(demo=bool(demo), data_manager=data_mgr)
            if block:
                # 仍尝试展示最近一次落盘摘要（按库内 K 线日），但禁止开扫
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
            # summary 优先（含合法的 0 机会）；CSV 仅作明细
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
                # 保留落盘摘要中的额外计数（如涨停）
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
            logger.debug("ScanJob.readiness failed strategy=%s", name, exc_info=True)
            return {"primary_action": "run", "can_scan": False, "block_reason": "读取扫描就绪状态失败"}

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

            settings = StrategySettings.from_dict(dict(info.settings or {}))
            settings.apply_defaults()
            cls.apply_scan_mode(settings, demo=bool(demo))

            block = cls.strict_block_reason(demo=bool(demo), data_manager=data_mgr)
            if block:
                raise ValueError(block)

            kline_latest = ScanDateResolver.load_kline_latest_date(data_mgr)
            if not kline_latest:
                raise ValueError("无法解析 K 线最新日期（sys_stock_klines 可能为空）")

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
