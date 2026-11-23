"""Scanner Pipeline — 扫描领域编排。

- ``scan``：CLI / 多策略
- ``run``：单策略（日期 → ScanStore / BE → ReportManager）
- ``page_context`` / ``readiness`` / ``block_reason``：工作台读模型（能否扫、已有落盘）

进度文件由 Facade ``Strategy.scan_run`` 写；本类不碰 ``ScanProgress`` 生命周期。
"""
from __future__ import annotations

import logging
from dataclasses import fields as dc_fields
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.modules.post_process import PostProcess
from core.modules.backtest_engine import BacktestEngine
from core.modules.data_manager import DataManager
from core.modules.strategy.core.engines.scanner.executor import ScannerJobExecutor
from core.modules.strategy.core.engines.scanner.helpers import (
    ScanDateResolver,
    ScannerCalendarAsof,
)
from core.modules.strategy.core.engines.scanner.helpers.price_history_enrichment import (
    enrich_post_process_ui_history,
)
from core.modules.strategy.core.engines.scanner.job_builder import ScannerJobBuilder
from core.modules.strategy.core.engines.scanner.report_manager import ReportManager
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.services.artifacts.store import ArtifactStore
from core.modules.strategy.core.services.artifacts.version_meta import VersionMetaStore
from core.modules.strategy.core.services.discovery import DiscoveryService
from core.modules.strategy.core.services.discovery.data.discovered_strategy import (
    EnabledStrategyInfo,
)
from core.modules.strategy.core.services.fingerprint import FingerprintCalculator

logger = logging.getLogger(__name__)


class ScannerPipeline:
    """扫描领域编排入口。"""

    @classmethod
    def scan_fingerprint(
        cls,
        strategy_info: EnabledStrategyInfo,
        settings: StrategySettings,
    ) -> str:
        """扫描结果身份：执行设置 + 环境（含 hooks），不含选股宇宙。

        用于判断落盘摘要是否仍对应当前策略；宇宙变化不强制作废当日缓存。
        """
        try:
            execute_fp = FingerprintCalculator.to_execute_fingerprint(
                settings,
                entity_ids=None,
            )
            env_fp = FingerprintCalculator.to_env_fingerprint(strategy_info)
            return FingerprintCalculator._to_fingerprint_hash(
                {"execute": execute_fp, "env": env_fp}
            )
        except Exception:
            logger.debug("scan_fingerprint failed", exc_info=True)
            return ""

    @classmethod
    def latest_workbench_version(cls, strategy_folder: Any) -> int:
        """磁盘上最新主号工作台版本（无则为 0）。"""
        try:
            root = ArtifactStore.simulations_root(strategy_folder)
            vids = VersionMetaStore.list_version_ids(root)
            return max((int(v) for v in vids), default=0)
        except Exception:
            logger.debug("latest_workbench_version failed", exc_info=True)
            return 0

    @staticmethod
    def _settings_stale(summary_payload: Dict[str, Any], current_fp: str) -> bool:
        stored = str(summary_payload.get("scan_fingerprint") or "").strip()
        cur = str(current_fp or "").strip()
        if not stored or not cur:
            return False
        return stored != cur

    @staticmethod
    def _version_stale(summary_payload: Dict[str, Any], current_version: int) -> bool:
        """工作台已有更新主号 → 扫描结果视为过时（环境/产物可能已变）。"""
        try:
            stored = int(summary_payload.get("workbench_version") or 0)
        except (TypeError, ValueError):
            stored = 0
        try:
            cur = int(current_version or 0)
        except (TypeError, ValueError):
            cur = 0
        return cur > 0 and stored < cur

    @classmethod
    def _scan_result_stale(
        cls,
        summary_payload: Dict[str, Any],
        *,
        current_fp: str,
        current_version: int,
    ) -> Tuple[bool, bool]:
        """返回 ``(settings_stale, version_stale)``。"""
        return (
            cls._settings_stale(summary_payload, current_fp),
            cls._version_stale(summary_payload, current_version),
        )

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
            logger.error("无法解析 K 线最新日期（sys_data_stock_klines 可能为空）")
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
            # 工作区后处理开关由 PostProcess prefs 持有（run 时检查）；此处只读给扫描页
            "enable_post_process": PostProcess.is_run_enabled(),
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

            current_fp = cls.scan_fingerprint(info, settings)
            current_wb_ver = cls.latest_workbench_version(folder)

            block = cls.block_reason(demo=bool(demo), data_manager=data_mgr)
            if block:
                kline_latest = ScanDateResolver.load_kline_latest_date(data_mgr)
                report = None
                primary = "run"
                settings_stale = False
                version_stale = False
                if kline_latest:
                    store = ArtifactStore.scan_at(folder, kline_latest)
                    summary_payload = store.read_summary()
                    if isinstance(summary_payload, dict):
                        opportunities = ReportManager.load_opportunities(store)
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
                        if isinstance(summary_payload.get("post_process"), dict):
                            report["post_process"] = enrich_post_process_ui_history(
                                dict(summary_payload["post_process"]),
                                fallback_strategy_name=str(
                                    summary_payload.get("strategy_key") or name or ""
                                ),
                            )
                        primary = "rerun"
                        settings_stale, version_stale = cls._scan_result_stale(
                            summary_payload,
                            current_fp=current_fp,
                            current_version=current_wb_ver,
                        )
                return {
                    "primary_action": primary,
                    "can_scan": False,
                    "block_reason": block,
                    "settings_stale": settings_stale,
                    "version_stale": version_stale,
                    **({"report": report} if report else {}),
                }

            resolver = ScanDateResolver(data_mgr)
            scan_date, stock_ids = resolver.resolve_scan_date(use_strict=use_strict)
            store = ArtifactStore.scan_at(folder, scan_date)
            summary_payload = store.read_summary()
            if not isinstance(summary_payload, dict):
                return {
                    "primary_action": "run",
                    "can_scan": True,
                    "block_reason": "",
                    "settings_stale": False,
                    "version_stale": False,
                }

            opportunities = ReportManager.load_opportunities(store)
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
            if isinstance(summary_payload.get("post_process"), dict):
                report["post_process"] = enrich_post_process_ui_history(
                    dict(summary_payload["post_process"]),
                    fallback_strategy_name=str(
                        summary_payload.get("strategy_key") or name or ""
                    ),
                )
            settings_stale, version_stale = cls._scan_result_stale(
                summary_payload,
                current_fp=current_fp,
                current_version=current_wb_ver,
            )
            return {
                "primary_action": "rerun",
                "can_scan": True,
                "block_reason": "",
                "settings_stale": settings_stale,
                "version_stale": version_stale,
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
        run_post_process: bool = True,
        on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
        data_manager: Any = None,
    ) -> Dict[str, Any]:
        """单策略扫描（日期 → ScanStore / BE → ReportManager）。"""
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
        ArtifactStore.prune_scan(strategy_folder, max_versions=scan_max)
        store = ArtifactStore.scan_at(strategy_folder, scan_date)
        current_fp = cls.scan_fingerprint(strategy_info, settings)
        current_wb_ver = cls.latest_workbench_version(strategy_folder)
        use_cache = (not force) and store.has_summary()
        if use_cache:
            existing = store.read_summary()
            if isinstance(existing, dict):
                settings_stale, version_stale = cls._scan_result_stale(
                    existing,
                    current_fp=current_fp,
                    current_version=current_wb_ver,
                )
                if settings_stale or version_stale:
                    # 设置/环境变了，或工作台已有更新版本 → 作废当日缓存
                    use_cache = False

        # 横截面策略：先切片选股再扫，避免 is_opportunity 对全宇宙放行
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
            goal=PostProcess.goal_summary_from_settings(settings.goal.goal),
            scan_fingerprint=current_fp,
            workbench_version=current_wb_ver,
            max_cache_days=scan_max,
            skip_save=use_cache,
        )

        if use_cache:
            report.collect(ReportManager.load_opportunities(store))
            if callable(on_progress):
                try:
                    on_progress(
                        {
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

        return report.finalize(present=True, run_post_process=bool(run_post_process))

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
