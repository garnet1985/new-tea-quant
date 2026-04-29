#!/usr/bin/env python3
"""Strategy info dataclass."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Type

from core.modules.strategy.engines.shared.data_classes.strategy_settings.strategy_settings import (
    StrategySettings,
)


@dataclass
class StrategyInfo:
    """Validated strategy metadata used by orchestrators."""

    name: str
    folder: Path
    worker_class: Type[Any]
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
        return bool(self.settings.is_enabled)

    def get_settings(self) -> StrategySettings:
        return self.settings
