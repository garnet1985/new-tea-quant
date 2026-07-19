"""Strategy Facade — scan / enumerate / price / portfolio / simulate / discovery API。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type, Union

from .contracts import SimulateKind
from .core.services.discovery import DiscoveryService
from .core.services.discovery.data.discovered_strategy import EnabledStrategyInfo
from .core.engines.shared.services.entity_loader.global_entity_loader import (
    GlobalEntityCache,
)
from .core.services.simulation_cache.cache_manager import (
    SimulationCacheManager,
)
from .core.services.simulation_cache.fingerprints import (
    FingerprintCalculator,
    FingerprintResult,
)


@dataclass
class SimulateRuntimeContext:
    """一次 simulate 的编排会话（Facade → Pipeline；不含 CacheManager）。

    每次 simulate 新建；不在内存里跨请求复用（settings / env 可能变）。
    """

    strategy_info: EnabledStrategyInfo
    fp_res: FingerprintResult
    kind: SimulateKind
    enum_version: Optional[str] = None
    steps: List[SimulateKind] = field(default_factory=list)

    @property
    def settings_fp(self) -> str:
        return self.fp_res.settings_fp

    @property
    def env_fp(self) -> str:
        return self.fp_res.env_fp

    @property
    def effective_settings(self):
        return self.fp_res.effective_settings

    @property
    def settings_diff(self):
        return self.fp_res.settings_diff

    @property
    def global_entity_cache(self):
        return self.fp_res.global_entity_cache

    @property
    def entity_ids(self) -> List[str]:
        return self.fp_res.entity_ids

    @property
    def strategy_key(self) -> str:
        return str(
            self.strategy_info.unique_relative_path or self.strategy_info.key or ""
        )

    def validate_for_run(self) -> None:
        """跑 Pipeline 前自检。"""
        if self.strategy_info is None:
            raise ValueError("SimulateRuntimeContext.strategy_info 不能为空")
        if self.fp_res is None:
            raise ValueError("SimulateRuntimeContext.fp_res 不能为空")
        if not self.settings_fp or not self.env_fp:
            raise ValueError("settings_fp / env_fp 不能为空")
        if self.fp_res.global_entity_cache is None:
            raise ValueError("global_entity_cache 不能为空")
        if self.kind == SimulateKind.FULL:
            raise ValueError("simulate(kind=full) 暂不支持")
        if not self.steps:
            raise ValueError("steps 为空：请先 _resolve_steps")
        if (
            self.kind != SimulateKind.ENUMERATE
            and self.enum_version is None
            and SimulateKind.ENUMERATE not in self.steps
        ):
            raise ValueError(
                f"{self.kind.value} 需要 enum_version 或 steps 中包含 enumerate"
            )


class BackTestPipelines:
    """kind → Pipeline 映射（按需 import；未落地的 step 访问时再报错）。"""

    ENUMERATE = SimulateKind.ENUMERATE
    PRICE_FACTOR = SimulateKind.PRICE_FACTOR
    CAPITAL_ALLOCATION = SimulateKind.CAPITAL_ALLOCATION

    @classmethod
    def __class_getitem__(cls, kind: SimulateKind) -> Type[Any]:
        if kind == SimulateKind.ENUMERATE:
            from .core.engines.enumerator import EnumeratorPipeline

            return EnumeratorPipeline
        raise NotImplementedError(f"Pipeline for {kind!r} 尚未接入")


class Strategy:
    """策略模块 Facade。

    模拟编排：先解析指纹 → 查对应 CacheManager → miss 再进引擎；
    引擎执行后由 Pipeline / 后续步骤写回缓存。
    """

    @staticmethod
    def scan(
        key_or_id: Optional[str] = None,
        *,
        demo: bool = False,
    ) -> Dict[str, Any]:
        """执行机会扫描。"""
        _ = demo
        raise NotImplementedError("Strategy.scan() implementation pending")

    @staticmethod
    def analyze(*, session_id: Optional[str] = None) -> None:
        """分析模拟结果。"""
        _ = session_id
        raise NotImplementedError("Strategy.analyze() implementation pending")

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
            kind=SimulateKind.CAPITAL_ALLOCATION,
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
        """统一模拟入口：枚举 / 价格 / 资金 / full。

        流程（各 step 共用）:
        1. 解析 settings_fp + env_fp
        2. 查该 step 缓存；命中则直接返回
        3. 未命中则执行（price/capital 必要时先补跑枚举）并写缓存
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

        ctx = SimulateRuntimeContext(
            strategy_info=strategy_info,
            fp_res=fp_res,
            kind=step,
        )

        cache_key = ctx.strategy_key or key_or_id
        res: Dict[str, Any] = {}

        if ignore_cache:
            Strategy._resolve_steps(ctx)
            ctx.validate_for_run()
            res = Strategy._run_steps(ctx)
            SimulationCacheManager.set_cache(cache_key, ctx.fp_res, res)
        else:
            cached_result = SimulationCacheManager.get_cache(
                cache_key, ctx.fp_res, ctx.kind
            )
            if cached_result:
                res = cached_result
            else:
                Strategy._resolve_steps(ctx)
                ctx.validate_for_run()
                res = Strategy._run_steps(ctx)
                SimulationCacheManager.set_cache(cache_key, ctx.fp_res, res)

        # TODO: should return a job id
        return res

    @staticmethod
    def _resolve_steps(ctx: SimulateRuntimeContext) -> None:
        """按目标 kind + fp 是否已有枚举产物，写入 ctx.steps / ctx.enum_version。"""
        from .core.engines.enumerator import EnumeratorPipeline

        step = ctx.kind
        if step == SimulateKind.ENUMERATE:
            ctx.steps = [SimulateKind.ENUMERATE]
            ctx.enum_version = None
            return

        enum_version = EnumeratorPipeline.find_output_version_via_fps(ctx)
        if enum_version:
            ctx.steps = [step]
            ctx.enum_version = enum_version
            return

        ctx.steps = [SimulateKind.ENUMERATE, step]
        ctx.enum_version = None

    @staticmethod
    def _run_steps(ctx: SimulateRuntimeContext) -> Dict[str, Any]:
        """依次执行 Pipeline（无 CacheManager）；入参为 runtime context。"""
        consolidated_result: Dict[str, Any] = {}
        for step in ctx.steps:
            step_res = BackTestPipelines[step].run(ctx)
            consolidated_result[step.value] = step_res
            if step == SimulateKind.ENUMERATE:
                version_id = step_res.get("version_id")
                if version_id:
                    ctx.enum_version = str(version_id)
        return consolidated_result

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


__all__ = ["Strategy", "SimulateRuntimeContext"]
