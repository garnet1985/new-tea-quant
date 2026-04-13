from typing import Dict, Any, Type
from pathlib import Path
from dataclasses import dataclass

from core.modules.strategy.base_strategy_worker import BaseStrategyWorker
from core.modules.strategy.data_classes.strategy_settings.strategy_settings import (
    StrategySettings,
)


@dataclass
class StrategyInfo:
    """
    策略信息。

    经 ``StrategyDiscoveryHelper.load_strategy`` 进入管理器的实例，其 ``settings`` 已在发现阶段
    通过 ``validate()``，可视为 **valid**。是否参与 scan 等由 **``is_enabled``**（``settings`` 上的开关）决定；
    ``StrategyManager`` 只缓存 ``validated_strategies`` 时，在循环里用 ``info.is_enabled`` 过滤即可。
    """
    name: str
    folder: Path
    worker_class: Type[BaseStrategyWorker]
    worker_module_path: str
    worker_class_name: str
    settings: StrategySettings

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "settings": self.settings.to_dict(),
            "folder": self.folder,
            "worker_class": self.worker_class,
            "worker_module_path": self.worker_module_path,
            "worker_class_name": self.worker_class_name,
        }

    @property
    def is_enabled(self) -> bool:
        """是否在配置中启用（与 ``settings.meta.is_enabled`` 一致）。"""
        return bool(self.settings.is_enabled)

    def get_settings(self) -> StrategySettings:
        return self.settings

