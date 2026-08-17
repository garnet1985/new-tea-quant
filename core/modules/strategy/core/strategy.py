"""Strategy 模块 Facade — scan / enumerate / price / portfolio / simulate / discovery。

本文件:
- Strategy: 对外 API（扫描委托 ScannerPipeline；simulate 指纹→缓存→Pipeline）
  边界: 负责公开入口与 simulate 跨 step 编排；scan 领域逻辑在 ScannerPipeline
- BackTestPipelines: SimulateKind → Pipeline 懒加载映射
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union, TextIO

from .enums import SimulateKind
from .services.discovery import DiscoveryService
from .services.entity_loader.global_entity_loader import (
    GlobalEntityCache,
)
from .engines.shared.data_class.simulate_session import SimulateSession
from .services.simulation_cache.cache_manager import (
    SimulationCacheManager,
)
from .services.simulation_cache.fingerprints import (
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
            from .engines.enumerator import EnumeratorPipeline

            return EnumeratorPipeline
        if kind == SimulateKind.PRICE_FACTOR:
            from .engines.price_factor import PriceFactorPipeline

            return PriceFactorPipeline
        if kind == SimulateKind.PORTFOLIO:
            from .engines.portfolio import PortfolioPipeline

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
                return dict(cached)
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
        from .engines.enumerator import EnumeratorPipeline

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
    def latest_completed_trading_date() -> str:
        """系统最新已收盘交易日（供 calculation 默认 end_date 等）。"""
        from .services.entity_loader.global_entity_loader import GlobalEntityCache

        return GlobalEntityCache.load_latest_completed_trading_date()

    @staticmethod
    def _to_info_dict(info: Any) -> Dict[str, Any]:
        folder = info.resolved_folder() if hasattr(info, "resolved_folder") else info.folder
        hooks_class = getattr(info, "hooks_class", None)
        hooks_name = ""
        if hooks_class is not None:
            try:
                hooks_name = str(getattr(hooks_class, "__name__", "") or "")
            except Exception:
                hooks_name = ""
        return {
            "relative_path": info.unique_relative_path,
            "unique_relative_path": info.unique_relative_path,
            "key": info.key,
            "is_enabled": bool(getattr(info, "is_enabled", False)),
            "display_name": info.display_name,
            "folder": str(folder),
            "settings": info.settings,
            "hooks_class_name": hooks_name,
        }

    @staticmethod
    def list_strategies(*, strategies_root: Optional[str] = None) -> List[str]:
        """返回已发现策略 id（unique_relative_path）列表。

        ``strategies_root`` 预留；当前始终使用 ProjectContext 策略根目录。
        """
        _ = strategies_root
        return [d["unique_relative_path"] for d in Strategy.list_strategy_infos()]

    @staticmethod
    def list_enabled_strategies(*, strategies_root: Optional[str] = None) -> List[str]:
        """返回启用策略 id（unique_relative_path）列表。"""
        _ = strategies_root
        return [
            d["unique_relative_path"]
            for d in Strategy.list_strategy_infos(enabled_only=True)
        ]

    @staticmethod
    def list_enabled_keys() -> List[str]:
        """已启用策略的 ``meta.key`` 列表（CLI 提示用）。"""
        return [
            str(d["key"])
            for d in Strategy.list_strategy_infos(enabled_only=True)
            if d.get("key")
        ]

    @staticmethod
    def list_strategy_infos(*, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """返回策略元数据列表（一次 discovery，供清理/目录类调用方批量使用）。"""
        strategies = (
            DiscoveryService.get_enabled_strategies()
            if enabled_only
            else DiscoveryService.discover_strategies()
        )
        return [Strategy._to_info_dict(info) for info in strategies]

    @staticmethod
    def find(
        key_or_id: str,
        *,
        enabled_only: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """按 ``meta.key`` 或相对路径查找；未命中返回 ``None``。"""
        needle = str(key_or_id or "").strip()
        if not needle:
            return None
        for info in Strategy.list_strategy_infos(enabled_only=enabled_only):
            if needle in (
                str(info.get("key") or "").strip(),
                str(info.get("unique_relative_path") or "").strip(),
                str(info.get("relative_path") or "").strip(),
            ):
                return info
        return None

    @staticmethod
    def get_strategy_info(
        strategy_name: str,
        *,
        strategies_root: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """返回策略元数据（认 key / 相对路径）；不存在时返回 None。"""
        _ = strategies_root
        return Strategy.find(strategy_name, enabled_only=False)

    @staticmethod
    def resolve(key_or_id: str) -> str:
        """``meta.key`` 或 path → 稳定身份 ``meta.key``（缺 key 时回落 path）。

        用于 DB / 进度 / UI 身份。磁盘定位请用 ``resolve_path`` / ``resolve_folder``。
        不存在则 ``FileNotFoundError``。
        """
        return DiscoveryService.resolve_strategy_key(key_or_id)

    @staticmethod
    def resolve_path(key_or_id: str) -> str:
        """``meta.key`` 或 path → userspace 相对 path（含未启用）。不存在则 ``FileNotFoundError``。"""
        return DiscoveryService.resolve_strategy_path(key_or_id)

    @staticmethod
    def resolve_folder(key_or_id: str) -> Path:
        """``meta.key`` / path → 绝对策略目录（未入库时回落 coerce）。"""
        return DiscoveryService.resolve_strategy_folder(key_or_id)

    @staticmethod
    def load_price_entity_investments(version_dir: Path, entity_id: str):
        """读取 price_factor version 下单实体 investments CSV（跨模块入口；勿 deep-import EntityInvestments）。"""
        from .engines.price_factor.report_manager.investments import EntityInvestments

        return EntityInvestments.load(version_dir, entity_id)

    @staticmethod
    def price_overall_report_path(version_dir: Path) -> Path:
        """price_factor version 目录下 ``overall_report.json`` 路径。"""
        from .engines.price_factor.report_manager.report_consts import ReportPaths

        return ReportPaths.overall_report_path(version_dir)

    @staticmethod
    def present_report(
        kind: Union[SimulateKind, str],
        output_dir: Union[str, Path],
        *,
        stream: Optional[TextIO] = None,
    ) -> None:
        """从 ``output_dir`` 展示 enumerate / price_factor / portfolio 终局摘要（CLI 入口）。"""
        if isinstance(kind, SimulateKind):
            key = kind
        else:
            key = SimulateKind(str(kind or "").strip().lower())
        path = Path(output_dir)
        if key is SimulateKind.ENUMERATE:
            from .engines.enumerator.common.report_manager import ReportManager
        elif key is SimulateKind.PRICE_FACTOR:
            from .engines.price_factor.report_manager import ReportManager
        elif key is SimulateKind.PORTFOLIO:
            from .engines.portfolio.report_manager import ReportManager
        else:
            raise ValueError(f"unsupported present_report kind: {kind!r}")
        ReportManager.from_output_dir(path).present(stream=stream)

    @staticmethod
    def is_valid_path(relative_path: str) -> bool:
        """脚手架路径段是否机器可读（ASCII 标识符段）。"""
        from .services.discovery.path_rules import StrategyPathRules

        return StrategyPathRules.is_machine_readable_path(relative_path)

    @staticmethod
    def clear_workbench_cache() -> int:
        """清空 ``sys_strategy_workbench_snapshot``；失败抛 ``RuntimeError``，成功返回删除行数。"""
        from .services.workbench_cache import WorkbenchCacheClear

        out = WorkbenchCacheClear.clear_all()
        if not out.get("ok"):
            raise RuntimeError(str(out.get("error") or "存储不可用"))
        return int(out.get("deleted_count") or 0)

    @staticmethod
    def prune_simulation_results(
        key_or_id: str,
        *,
        kind: Optional[str] = None,
        max_versions: Optional[int] = None,
    ) -> Dict[str, Any]:
        """按 retention 清理策略 ``results/simulations/{kind}/`` 旧版本目录。

        ``kind`` 为 ``enum`` / ``price`` / ``portfolio``（或 enumerate/price_factor）；
        ``None`` 表示三步都 prune。上限默认读 ``data.json`` retention。
        """
        from .services.results_retention import ResultsRetention

        return ResultsRetention.prune_simulation_results(
            key_or_id, kind=kind, max_versions=max_versions
        )

    @staticmethod
    def prune_scan_results(
        key_or_id: str,
        *,
        max_versions: Optional[int] = None,
    ) -> Dict[str, Any]:
        """按 retention 清理策略 ``results/scan/`` 旧日期版本。"""
        from .services.results_retention import ResultsRetention

        return ResultsRetention.prune_scan_results(
            key_or_id, max_versions=max_versions
        )

    @staticmethod
    def export_package(
        target: str,
        *,
        output_path: Optional[str] = None,
    ) -> int:
        """导出策略包（bundle / 单实体语法同 CLI）；返回进程退出码。"""
        from .services.package import PackageCli

        return PackageCli.run_export(target, output_path=output_path)

    @staticmethod
    def import_package(
        package_path: str,
        *,
        force: bool = False,
        skip_existing: bool = False,
        dry_run: bool = False,
    ) -> int:
        """导入策略 bundle；返回进程退出码。"""
        from .services.package import PackageCli

        return PackageCli.run_strategy_bundle_import(
            package_path,
            force=force,
            skip_existing=skip_existing,
            dry_run=dry_run,
        )


__all__ = ["Strategy", "BackTestPipelines"]
