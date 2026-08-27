"""Strategy 模块 Facade — scan / enumerate / price / portfolio / simulate / discovery。

本文件:
- Strategy: 对外 API（扫描委托 ScannerPipeline；simulate 指纹→磁盘 registry→Pipeline）
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
from .engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from .services.artifacts import SimulationVersionStore
from .services.fingerprint import (
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

    模拟编排：算指纹 → 查磁盘 registry → miss 则 resolve steps（必要时先 enum）
    → 每步 Pipeline.run 后写 registry + effective_settings。
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

        缓存与指纹流程（磁盘单轨）::

            1. 计算 settings_fp / env_fp
            2. 扫 ``simulations/meta.json`` registry；step 产物存在则命中
            3. 未命中：price/portfolio 先按指纹找 enum vid；无则先 enum 再本 step
            4. 每步完成后 ``SimulationVersionStore.record_step_complete``
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
            entity_ids=stock_list,
        )

        ctx = SimulateSession.create(
            strategy_info=strategy_info,
            fp_res=fp_res,
            kind=step,
            seed_entity_cache=False,
        )
        cache_key = ctx.strategy_key or key_or_id

        strategy_folder = DiscoveryService.resolve_strategy_folder(key_or_id)

        if not ignore_cache:
            cached = SimulationVersionStore.get_cache(
                strategy_folder,
                fp_res,
                ctx.kind,
            )
            if cached:
                logger.info(
                    "simulate cache hit: kind=%s strategy=%s",
                    ctx.kind.value,
                    cache_key,
                )
                return Strategy._attach_version_id(dict(cached), ctx.kind)
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

        ctx.prepare_entity_cache(
            stock_list=stock_list,
            latest_completed_trading_date=latest_completed_trading_date,
        )
        Strategy._resolve_steps(ctx, ignore_cache=ignore_cache)
        ctx.validate_for_run()
        return Strategy._run_steps(
            ctx,
            strategy_folder=strategy_folder,
            ignore_cache=ignore_cache,
        )

    @staticmethod
    def _maybe_run_analysis(
        step: SimulateKind,
        step_res: Dict[str, Any],
        ctx: SimulateSession,
        strategy_folder: Path,
        *,
        force: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """``settings.analysis.enabled`` 时在 simulate 主 step 完成后跑 analyze。"""
        if step != ctx.kind:
            return None
        if step_res.get("success") is False:
            return {"skipped": True, "reason": "simulate_failed"}
        if not ctx.effective_settings.analysis.enabled:
            return {"skipped": True, "reason": "disabled"}

        output_dir = str(step_res.get("output_dir") or "").strip()
        version_id = str(step_res.get("version_id") or "").strip()
        if not output_dir:
            return {"skipped": True, "reason": "missing_output_dir"}

        from .engines.analyzer import Analyzer
        from .services.artifacts import ArtifactStore

        store = ArtifactStore.open(
            Path(output_dir),
            kind=step,
            version_id=version_id or None,
        )
        try:
            return Analyzer.run(store, strategy_folder=strategy_folder, force=force)
        except Exception as exc:
            logger.exception(
                "analysis step failed: strategy=%s step=%s",
                ctx.strategy_key,
                step.value,
            )
            return {"skipped": True, "reason": "error", "error": str(exc)}

    @staticmethod
    def _resolve_simulation_output_dir_candidates(
        strategy_name: str,
        *,
        step: str,
        slot: Optional[Dict[str, Any]] = None,
        workbench_version: int = 0,
    ) -> List[Path]:
        from .enums import WorkbenchStep
        from .services.artifacts import ArtifactStore

        sn = str(strategy_name or "").strip()
        if not sn:
            return []

        slot = slot if isinstance(slot, dict) else {}
        workbench_step = WorkbenchStep.parse(step)
        kind = workbench_step.to_simulate_kind()
        folder = Strategy.resolve_folder(sn)
        root = ArtifactStore.simulations_root(folder)
        step_dir = ArtifactStore.step_dir_name(kind)

        names: List[str] = []
        out_d = str(slot.get("output_dir") or "").strip()
        if out_d:
            names.append(out_d)
        vid = slot.get("version_id")
        if vid is not None:
            text = str(vid).strip().lstrip("vV")
            if text:
                names.append(text)
        if workbench_version > 0:
            names.append(str(int(workbench_version)))

        seen: set[str] = set()
        out: List[Path] = []
        for name in names:
            if not name or name in seen:
                continue
            seen.add(name)
            path = Path(name)
            if not path.is_absolute():
                path = root / name / step_dir
            out.append(path)
        return out

    @staticmethod
    def _resolve_steps(ctx: SimulateSession, *, ignore_cache: bool = False) -> None:
        """按目标 kind + 指纹是否已有枚举产物，写入 ctx.steps / ctx.enum_version。"""
        from .engines.enumerator import EnumeratorPipeline

        step = ctx.kind
        if ignore_cache:
            if step == SimulateKind.ENUMERATE:
                ctx.steps = [SimulateKind.ENUMERATE]
            else:
                ctx.steps = [SimulateKind.ENUMERATE, step]
            ctx.enum_version = None
            return

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
        strategy_folder: Union[str, Path],
        ignore_cache: bool = False,
    ) -> Dict[str, Any]:
        """依次执行 Pipeline；每步完成后更新磁盘 registry。"""
        consolidated: Dict[str, Any] = {}
        folder = Path(strategy_folder)
        semantic = StrategySettings.extract_effective_settings(ctx.effective_settings)
        for step in ctx.steps:
            step_res = BackTestPipelines[step].run(ctx)
            consolidated[step.value] = step_res
            if step == SimulateKind.ENUMERATE:
                version_id = step_res.get("version_id")
                if version_id:
                    ctx.enum_version = str(version_id)

            if step_res.get("version_id") and step_res.get("output_dir"):
                SimulationVersionStore.record_step_complete(
                    folder,
                    version_id=str(step_res.get("version_id")),
                    fps=ctx.fp_res,
                    settings=semantic,
                    entity_ids=list(ctx.entity_ids or []),
                )

            analysis_out = Strategy._maybe_run_analysis(
                step,
                step_res,
                ctx,
                folder,
                force=ignore_cache,
            )
            if analysis_out is not None:
                step_res["analysis"] = analysis_out

            logger.info(
                "simulate step complete: kind=%s strategy=%s version_id=%s",
                step.value,
                ctx.strategy_key,
                step_res.get("version_id"),
            )
        return Strategy._attach_version_id(consolidated, ctx.kind)

    @staticmethod
    def _attach_version_id(
        payload: Dict[str, Any],
        kind: SimulateKind,
    ) -> Dict[str, Any]:
        """把 step 槽里的 ``version_id`` 提到顶层，cache hit / miss 同一形状。"""
        primary = payload.get(kind.value)
        if isinstance(primary, dict):
            vid = str(primary.get("version_id") or "").strip()
            if vid:
                payload["version_id"] = vid
        return payload

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
        """读取 price_factor version 下单实体 investments CSV。"""
        from .services.artifacts import PriceFactorStore

        return PriceFactorStore.at(version_dir).investments(entity_id)

    @staticmethod
    def price_overall_report_path(version_dir: Path) -> Path:
        """price_factor version 目录下 ``overall_report.json`` 路径。"""
        from .services.artifacts import PriceFactorStore

        return PriceFactorStore.at(version_dir).file("overall_report")

    @staticmethod
    def step_analysis_from_output_dir(output_dir: Union[str, Path]) -> Dict[str, Any]:
        """Read ``analysis/report.json`` insights payload for one step output dir."""
        from .engines.analyzer.steps.report import ReportStep

        return ReportStep.load_payload(Path(output_dir))

    @staticmethod
    def resolve_step_analysis(
        strategy_name: str,
        step: str,
        slot: Optional[Dict[str, Any]] = None,
        *,
        workbench_version: int = 0,
    ) -> Dict[str, Any]:
        """Resolve step output dir(s) and load attribution insights payload."""
        from .engines.analyzer.steps.report import ReportStep

        for output_dir in Strategy._resolve_simulation_output_dir_candidates(
            strategy_name,
            step=str(step or "").strip(),
            slot=slot if isinstance(slot, dict) else {},
            workbench_version=int(workbench_version or 0),
        ):
            if not output_dir.is_dir():
                continue
            payload = ReportStep.load_payload(output_dir)
            if payload.get("available"):
                return payload
        return {
            "available": False,
            "report_path": "",
            "insights": None,
        }

    @staticmethod
    def resolve_simulation_output_dirs(
        strategy_name: str,
        *,
        step: str,
        slot: Optional[Dict[str, Any]] = None,
        workbench_version: int = 0,
    ) -> List[Path]:
        """Absolute version-dir candidates for enum / price / portfolio."""
        return Strategy._resolve_simulation_output_dir_candidates(
            strategy_name,
            step=step,
            slot=slot,
            workbench_version=workbench_version,
        )

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
    def present_analysis_report(
        output_dir: Union[str, Path],
        *,
        stream: Optional[TextIO] = None,
    ) -> None:
        """从仿真 ``output_dir`` 展示归因 ``analysis/report.json`` 终端摘要。"""
        from .engines.analyzer import Analyzer

        Analyzer.Presenter.load(output_dir).present(stream=stream)

    @staticmethod
    def is_valid_path(relative_path: str) -> bool:
        """脚手架路径段是否机器可读（ASCII 标识符段）。"""
        from .services.discovery.path_rules import StrategyPathRules

        return StrategyPathRules.is_machine_readable_path(relative_path)

    @staticmethod
    def prune_simulation_results(
        key_or_id: str,
        *,
        kind: Optional[str] = None,
        max_versions: Optional[int] = None,
    ) -> Dict[str, Any]:
        """按 retention 清理策略 ``results/simulations/`` 旧 version 目录。

        ``kind`` 为 ``enum`` / ``price`` / ``portfolio``（或 enumerate/price_factor）；
        ``None`` 表示三步都 prune。上限默认读 ``data.json`` retention。
        """
        from .services.artifacts import ArtifactRetention

        return ArtifactRetention.prune_simulation_results(
            key_or_id, kind=kind, max_versions=max_versions
        )

    @staticmethod
    def prune_scan_results(
        key_or_id: str,
        *,
        max_versions: Optional[int] = None,
    ) -> Dict[str, Any]:
        """按 retention 清理策略 ``results/scan/`` 旧日期版本。"""
        from .services.artifacts import ArtifactRetention

        return ArtifactRetention.prune_scan_results(
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
