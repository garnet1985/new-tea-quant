from typing import Dict, Any, Type
from pathlib import Path
from dataclasses import dataclass

from core.modules.strategy.base_strategy_worker import BaseStrategyWorker
from core.modules.strategy.data_classes.strategy_settings.meta_settings import BaseSettings


@dataclass
class StrategyInfo:
    """
    策略信息
    """
    name: str
    folder: Path
    worker_class: Type[BaseStrategyWorker]
    worker_module_path: str
    worker_class_name: str
    settings: BaseSettings

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "settings": self.settings.to_dict(),
            "folder": self.folder,
            "worker_class": self.worker_class,
            "worker_module_path": self.worker_module_path,
            "worker_class_name": self.worker_class_name,
        }

    def is_usable(self) -> bool:
        return self.settings.is_valid() and self.settings.is_enabled

    def get_settings(self) -> BaseSettings:
        return self.settings

