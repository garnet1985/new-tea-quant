"""Strategy Facade — scan / enumerate / analyze / discovery API。"""

from typing import Any, Dict, List, Optional

from .core.services.discovery import DiscoveryService


class Strategy:
    """策略模块 Facade。"""

    @staticmethod
    def scan(
        strategy_name: Optional[str] = None,
        *,
        demo: bool = False,
    ) -> Dict[str, Any]:
        """执行机会扫描。"""
        _ = demo
        # TODO: 实现 scan（entity_based scanner pipeline）
        raise NotImplementedError("Strategy.scan() implementation pending")

    @staticmethod
    def analyze(*, session_id: Optional[str] = None) -> None:
        """分析模拟结果。"""
        _ = session_id
        # TODO: 实现 analyze
        raise NotImplementedError("Strategy.analyze() implementation pending")

    @staticmethod
    def enumerate(key_or_id: str, ignore_cache: bool = False) -> Dict[str, Any]:
        """对单个策略运行枚举器。"""
        # from pathlib import Path

        from .core.engines.enumerator import EnumeratorEngine

        strategy = DiscoveryService.find_strategy(key_or_id)

        if strategy is None:
            raise ValueError(f"当前策略不存在或未启用: {key_or_id}")

        enumerator = EnumeratorEngine(strategy)
        return enumerator.run(ignore_cache=ignore_cache)

    @staticmethod
    def list_strategies(*, strategies_root: Optional[str] = None) -> List[str]:
        """返回已发现策略relative_path列表。"""
        from pathlib import Path

        strategies_path = Path(strategies_root) if strategies_root else None
        strategies = DiscoveryService.discover_strategies(strategies_path)
        return [info.relative_path for info in strategies]

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
