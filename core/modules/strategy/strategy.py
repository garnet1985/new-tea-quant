"""Strategy Facade — scan / enumerate / analyze / discovery API。"""

from typing import Any, Dict, List, Optional

from .core.services import DiscoveryService


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
    def enumerate(
        strategy_name: str,
        *,
        userspace_root: Optional[str] = None,
        strategies_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        """对单个策略运行 entity_based 枚举器。"""
        from pathlib import Path

        from .core.engines.enumerator import EnumeratorEngine
        from .core.services.data.output_paths import OutputPathManager
        from .core.services.data.params_resolver import BacktestParamsResolver
        from .core.services.settings.settings_loader import SettingsLoader

        strategies_path = Path(strategies_root) if strategies_root else None
        discovered = DiscoveryService.discover_strategies(strategies_path)
        strategy_info = discovered.get(strategy_name)
        if not strategy_info:
            raise ValueError(f"Strategy not found: {strategy_name}")

        strategy_folder = Path(strategy_info["folder"])
        settings_dict = SettingsLoader.load_settings_dict_from_folder(strategy_folder)
        params = BacktestParamsResolver.resolve_all_params(strategy_folder, settings_dict)

        userspace_path = Path(userspace_root) if userspace_root else Path("userspace")
        paths = OutputPathManager.resolve_all_paths(
            strategy_name,
            userspace_root=userspace_path,
        )

        engine = EnumeratorEngine(
            strategy_name=strategy_name,
            output_dir=paths["output_dir"],
            version_id=paths["version_id"],
            version_dir_name=paths["version_dir_name"],
            start_date=params["start_date"],
            end_date=params["end_date"],
            entity_ids=params["stock_list"],
            disk_settings=settings_dict,
            user_settings=settings_dict,
        )
        return engine.run(strategy_info)

    @staticmethod
    def list_strategies(*, strategies_root: Optional[str] = None) -> List[str]:
        """返回已发现策略名称列表。"""
        from pathlib import Path

        strategies_path = Path(strategies_root) if strategies_root else None
        discovered = DiscoveryService.discover_strategies(strategies_path)
        return sorted(discovered.keys())

    @staticmethod
    def get_strategy_info(
        strategy_name: str,
        *,
        strategies_root: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """返回策略元数据；不存在时返回 None。"""
        from pathlib import Path

        strategies_path = Path(strategies_root) if strategies_root else None
        discovered = DiscoveryService.discover_strategies(strategies_path)
        strategy_info = discovered.get(strategy_name)
        if strategy_info is None:
            return None
        return {
            "name": strategy_info["name"],
            "is_enabled": strategy_info["is_enabled"],
            "display_name": strategy_info["display_name"],
            "folder": strategy_info["folder"],
            "settings": strategy_info["settings"],
        }


__all__ = ["Strategy"]
