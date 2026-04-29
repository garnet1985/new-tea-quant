#!/usr/bin/env python3
"""Discovered strategy dataclass."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Type

from core.modules.strategy.engines.shared.data_classes.strategy_settings.strategy_settings import (
    StrategySettings,
)


@dataclass
class DiscoveredStrategy:
    """Discovery output containing parsed worker and validated settings."""

    name: str
    folder: Path
    worker_class: Type[Any]
    worker_module_path: str
    worker_class_name: str
    settings: StrategySettings

    def validate_required_fields(self) -> None:
        if not self.name:
            raise ValueError("strategy name is required")
        if not isinstance(self.folder, Path):
            raise ValueError("strategy folder must be a Path")
        if not self.worker_module_path or not self.worker_class_name:
            raise ValueError("worker module/class reference is required")
        if self.worker_class is None:
            raise ValueError("worker class is required")
        if self.settings is None:
            raise ValueError("validated strategy settings are required")

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


__all__ = ["DiscoveredStrategy"]
