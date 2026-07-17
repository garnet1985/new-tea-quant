"""Strategy Facade — scan / enumerate / price / portfolio / simulate / discovery API。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Type, Union

from .contracts import SimulateKind
from .core.services.discovery import DiscoveryService


class RunPipelines:
    SimulateKind.ENUMERATE: EnumeratorPipeline
    SimulateKind.PRICE_FACTOR: PriceFactorPipeline
    SimulateKind.CAPITAL_ALLOCATION: PortfolioPipeline

class SimulationFingerprint:
    settings: str
    env: str

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

        fps, effective_settings = SimulationCacheManager.fingerprint.calc(key_or_id, runtime_settings)
        res = {}

        if ignore_cache:
            steps = self._resolve_steps(kind)
            res = self._run_steps(steps, fps, effective_settings)
            SimulationCacheManager.set_cache(key_or_id, fps, res)
        else:
            cached_result = SimulationCacheManager.get_cache(key_or_id, fps, kind)
            if cached_result:
                res = cached_result
            else:
                steps = self._resolve_steps(kind)
                res = self._run_steps(steps, fps, effective_settings)
                SimulationCacheManager.set_cache(key_or_id, fps, res)
        return res

    def _resolve_steps(self, kind: SimulateKind) -> List[Type[Any]]:
        steps = []
        if kind != SimulateKind.ENUMERATE:
            output_version = EnumeratorPipeline.find_output_version_via_fps(fps)
            if output_version:
                steps = [RunPipelines[kind]]
            else:
                steps = [RunPipelines[RunPipelines.ENUMERATE], RunPipelines[kind]]
        else:
            steps = [RunPipelines[RunPipelines.ENUMERATE]]
        return steps

    def _run_steps(self, steps: List[Type[Any]], fps: SimulationFingerprint, runtime_settings: Dict[str, Any]) -> Dict[str, Any]:
        consolidated_result = {}
        for step in steps:
            result = step.run(fps, runtime_settings)
            consolidated_result.update(result)
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


__all__ = ["Strategy"]
