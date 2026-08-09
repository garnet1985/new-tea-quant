"""Strategy 模块 Facade — scan / enumerate / price / portfolio / simulate / discovery。

本文件:
- Strategy: 对外 API（扫描委托 ScannerPipeline；simulate 指纹→缓存→Pipeline）
  边界: 负责公开入口与 simulate 跨 step 编排；scan 领域逻辑在 ScannerPipeline
- BackTestPipelines: SimulateKind → Pipeline 懒加载映射
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Type, Union

from .core.enums import SimulateKind
from .core.services.discovery import DiscoveryService
from .core.services.entity_loader.global_entity_loader import (
    GlobalEntityCache,
)
from .core.engines.shared.data_class.simulate_session import SimulateSession
from .core.services.simulation_cache.cache_manager import (
    SimulationCacheManager,
)
from .core.services.simulation_cache.fingerprints import (
    FingerprintCalculator,
)

logger = logging.getLogger(__name__)


class BackTestPipelines:
    """SimulateKind → Pipeline 懒加载映射。

    边界: 负责按 kind 解析 Pipeline 类；不负责 run / 缓存 / 指纹。
    """

    @classmethod
    def __class_getitem__(cls, kind: SimulateKind) -> Type[Any]:
        if kind == SimulateKind.ENUMERATE:
            from .core.engines.enumerator import EnumeratorPipeline

            return EnumeratorPipeline
        if kind == SimulateKind.PRICE_FACTOR:
            from .core.engines.price_factor import PriceFactorPipeline

            return PriceFactorPipeline
        if kind == SimulateKind.PORTFOLIO:
            from .core.engines.portfolio import PortfolioPipeline

            return PortfolioPipeline
        raise NotImplementedError(f"Pipeline for {kind!r} 尚未接入")


class Strategy:
    """策略模块 Facade。

    模拟编排：算指纹 → 查目标 kind 槽 → miss 则 resolve steps（必要时先 enum）
    → 每步 Pipeline.run 后 ``set_cache`` 写自己的 slot。
    """

    @staticmethod
    def scan(
        key_or_id: Optional[str] = None,
        *,
        demo: bool = False,
    ) -> Dict[str, Any]:
        """执行机会扫描（委托 ``ScannerPipeline.scan``）。"""
        from core.modules.strategy.core.engines.scanner import ScannerPipeline

        return ScannerPipeline.scan(key_or_id, demo=demo)

    @staticmethod
    def analyze(*, session_id: Optional[str] = None) -> None:
        """读取各启用策略下 price / portfolio 最新 version 摘要并 present。

        ``session_id`` 预留，当前未使用。
        """
        import json
        from pathlib import Path

        from core.infra.project_context import ProjectContext

        _ = session_id

        enabled = DiscoveryService.get_enabled_strategies()
        if not enabled:
            logger.warning("没有启用的策略可分析")
            return

        def _latest_version_dir(root: Path) -> Optional[Path]:
            meta_path = root / "meta.json"
            if not meta_path.is_file():
                return None
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception:
                return None
            try:
                latest_id = int(meta.get("next_output_version") or 1) - 1
            except (TypeError, ValueError):
                return None
            if latest_id <= 0:
                return None
            version_dir = root / str(latest_id)
            return version_dir if version_dir.is_dir() else None

        found = False
        for info in enabled:
            sn = str(info.unique_relative_path or info.key or "").strip()
            if not sn:
                continue
            folder = info.resolved_folder()
            pf_root = ProjectContext.path.get_strategy_simulation_price_directory(
                folder
            )
            po_root = ProjectContext.path.get_strategy_simulation_portfolio_directory(
                folder
            )
            pf_latest = _latest_version_dir(pf_root)
            po_latest = _latest_version_dir(po_root)
            if not pf_latest and not po_latest:
                continue

            found = True
            logger.info("📊 strategy=%s", sn)

            if pf_latest:
                try:
                    from core.modules.strategy.core.engines.price_factor.report_manager import (
                        ReportManager as PriceReportManager,
                    )

                    PriceReportManager.from_output_dir(pf_latest).present()
                except Exception as exc:
                    logger.warning(
                        "   price_factor: version=%s present failed: %s",
                        pf_latest.name,
                        exc,
                    )

            if po_latest:
                try:
                    from core.modules.strategy.core.engines.portfolio.report_manager import (
                        ReportManager as PortfolioReportManager,
                    )

                    PortfolioReportManager.from_output_dir(po_latest).present()
                except Exception as exc:
                    logger.warning(
                        "   portfolio: version=%s present failed: %s",
                        po_latest.name,
                        exc,
                    )

        if not found:
            logger.warning(
                "未找到可分析的 simulations 结果（请先运行 strategy_price_factor / strategy_portfolio）"
            )

    @staticmethod
    def enumerate(
        key_or_id: str,
        ignore_cache: bool = False,
        runtime_settings: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """对单个策略运行枚举器（先查缓存，再进 EnumeratorPipeline）。"""
        return Strategy.simulate(
            key_or_id,
            kind=SimulateKind.ENUMERATE,
            ignore_cache=ignore_cache,
            runtime_settings=runtime_settings,
        )

    @staticmethod
    def price_factor(
        key_or_id: str,
        ignore_cache: bool = False,
        runtime_settings: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """价格因子回测（依赖枚举产物）。"""
        return Strategy.simulate(
            key_or_id,
            kind=SimulateKind.PRICE_FACTOR,
            ignore_cache=ignore_cache,
            runtime_settings=runtime_settings,
        )

    @staticmethod
    def portfolio(
        key_or_id: str,
        ignore_cache: bool = False,
        runtime_settings: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """资金/组合回测（依赖上游产物）。"""
        return Strategy.simulate(
            key_or_id,
            kind=SimulateKind.PORTFOLIO,
            ignore_cache=ignore_cache,
            runtime_settings=runtime_settings,
        )

    @staticmethod
    def simulate(
        key_or_id: str,
        *,
        kind: Union[SimulateKind, str] = SimulateKind.ENUMERATE,
        ignore_cache: bool = False,
        runtime_settings: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """统一模拟入口：枚举 / 价格 / 资金。

        缓存与指纹流程（各 step 共用）::

            1. 计算 settings_fp / env_fp（与磁盘 settings ⊕ runtime 对齐）
            2. 查目标 kind 槽位缓存；命中则直接返回
            3. 未命中：
               - price/portfolio：先按指纹找 enum version
                 · 有 → 只跑本 step（enum_version 来自缓存 / 枚举产物）
                 · 无 → 先跑 enumerate，再跑本 step
            4. 每完成一个 step 即 ``set_cache`` 合并写入该 step 的 slot
               （写入 enum 会清掉下游 price/portfolio 槽）
        """
        strategy_info = DiscoveryService.find_strategy(key_or_id)
        if strategy_info is None:
            raise ValueError(f"当前策略不存在或未启用: {key_or_id}")

        step = (
            kind
            if isinstance(kind, SimulateKind)
            else SimulateKind(str(kind).strip().lower())
        )
        if step == SimulateKind.FULL:
            raise ValueError("simulate(kind=full) 暂不支持")

        stock_list = GlobalEntityCache.get_stock_list()
        latest_completed_trading_date = (
            GlobalEntityCache.get_latest_completed_trading_date()
        )
        fp_res = FingerprintCalculator.calculate_fingerprints(
            strategy_info,
            runtime_settings,
            stock_list,
            latest_completed_trading_date,
        )

        ctx = SimulateSession.create(
            strategy_info=strategy_info,
            fp_res=fp_res,
            kind=step,
        )
        cache_key = ctx.strategy_key or key_or_id

        if not ignore_cache:
            cached = SimulationCacheManager.get_cache(cache_key, ctx.fp_res, ctx.kind)
            if cached:
                logger.info(
                    "simulate cache hit: kind=%s strategy=%s",
                    ctx.kind.value,
                    cache_key,
                )
                row = SimulationCacheManager._load_row_by_fingerprints(
                    cache_key,
                    ctx.fp_res.settings_fp,
                    ctx.fp_res.env_fp,
                    disk_settings_hash=str(
                        getattr(ctx.fp_res, "disk_settings_hash", "") or ""
                    ),
                )
                out = dict(cached)
                out["_workbench_version"] = int((row or {}).get("version") or 0)
                return out
            logger.info(
                "simulate cache miss: kind=%s strategy=%s",
                ctx.kind.value,
                cache_key,
            )
        else:
            logger.info(
                "simulate ignore_cache: kind=%s strategy=%s",
                ctx.kind.value,
                cache_key,
            )

        Strategy._resolve_steps(ctx)
        ctx.validate_for_run()
        return Strategy._run_steps(ctx, cache_key=cache_key)

    @staticmethod
    def _resolve_steps(ctx: SimulateSession) -> None:
        """按目标 kind + 指纹是否已有枚举产物，写入 ctx.steps / ctx.enum_version。"""
        from .core.engines.enumerator import EnumeratorPipeline

        step = ctx.kind
        if step == SimulateKind.ENUMERATE:
            ctx.steps = [SimulateKind.ENUMERATE]
            ctx.enum_version = None
            return

        enum_version = EnumeratorPipeline.find_output_version_via_fps(ctx)
        if enum_version:
            logger.info(
                "reuse enum version via fingerprints: %s (strategy=%s)",
                enum_version,
                ctx.strategy_key,
            )
            ctx.steps = [step]
            ctx.enum_version = enum_version
            return

        logger.info(
            "enum version missing for fingerprints; will run enumerate then %s",
            step.value,
        )
        ctx.steps = [SimulateKind.ENUMERATE, step]
        ctx.enum_version = None

    @staticmethod
    def _run_steps(
        ctx: SimulateSession,
        *,
        cache_key: str,
    ) -> Dict[str, Any]:
        """依次执行 Pipeline；每步完成后按指纹更新对应 cache slot。"""
        consolidated: Dict[str, Any] = {}
        last_wb_version = 0
        for step in ctx.steps:
            step_res = BackTestPipelines[step].run(ctx)
            consolidated[step.value] = step_res
            if step == SimulateKind.ENUMERATE:
                version_id = step_res.get("version_id")
                if version_id:
                    ctx.enum_version = str(version_id)

            # 逐步写 slot：enum 先落盘后，即使下游 price 失败，指纹→enum version 仍可复用
            wb_version = SimulationCacheManager.set_cache(
                cache_key,
                ctx.fp_res,
                {step.value: step_res},
            )
            if int(wb_version or 0) > 0:
                last_wb_version = int(wb_version)
            logger.info(
                "simulate cache updated: kind=%s strategy=%s version_id=%s workbench=%s",
                step.value,
                cache_key,
                step_res.get("version_id"),
                last_wb_version,
            )
        consolidated["_workbench_version"] = last_wb_version
        return consolidated

    @staticmethod
    def list_strategies(*, strategies_root: Optional[str] = None) -> List[str]:
        """返回已发现策略relative_path列表。"""
        from pathlib import Path

        strategies_path = Path(strategies_root) if strategies_root else None
        strategies = DiscoveryService.discover_strategies(strategies_path)
        return [info.id() for info in strategies]

    @staticmethod
    def list_enabled_strategies(*, strategies_root: Optional[str] = None) -> List[str]:
        """返回启用策略relative_path列表。"""
        from pathlib import Path

        strategies_path = Path(strategies_root) if strategies_root else None
        strategies = DiscoveryService.discover_enabled_strategies(strategies_path)
        return [info.relative_path for info in strategies]

    @staticmethod
    def get_strategy_info(
        strategy_name: str,
        *,
        strategies_root: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """返回策略元数据；不存在时返回 None。"""
        from pathlib import Path

        strategies_path = Path(strategies_root) if strategies_root else None
        strategies = DiscoveryService.discover_strategies(strategies_path)
        for info in strategies:
            if info.relative_path == strategy_name:
                return {
                    "relative_path": info.relative_path,
                    "key": info.key,
                    "is_enabled": info.is_enabled,
                    "display_name": info.display_name,
                    "folder": str(info.folder),
                    "settings": info.settings,
                }
        return None


__all__ = ["Strategy", "BackTestPipelines"]
