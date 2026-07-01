"""Discovered strategy entity."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Type

from ..settings.strategy_settings import StrategySettings


@dataclass
class DiscoveredStrategy:
    """Discovered strategy entity containing parsed worker and validated settings."""

    name: str
    folder: Path
    worker_class: Type[Any]
    worker_module_path: str
    worker_class_name: str
    worker_file_path: Path
    settings: StrategySettings

    def validate_required_fields(self) -> None:
        """Validate required fields are present."""
        if not self.name:
            raise ValueError('strategy name is required')
        if not isinstance(self.folder, Path):
            raise ValueError('strategy folder must be a Path')
        if not self.worker_module_path or not self.worker_class_name:
            raise ValueError('worker module/class reference is required')
        if not isinstance(self.worker_file_path, Path):
            raise ValueError('worker_file_path must be a Path')
        if self.worker_class is None:
            raise ValueError('worker class is required')
        if self.settings is None:
            raise ValueError('validated strategy settings are required')

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for serialization."""
        return {
            'name': self.name,
            'settings': self.settings.to_dict(),
            'folder': str(self.folder),
            'worker_class': self.worker_class.__name__,
            'worker_module_path': self.worker_module_path,
            'worker_class_name': self.worker_class_name,
            'worker_file_path': str(self.worker_file_path),
        }

    @property
    def is_enabled(self) -> bool:
        """Check if strategy is enabled."""
        return bool(self.settings.is_enabled)

    @property
    def display_name(self) -> str:
        """Get strategy display name."""
        return self.settings.display_name

    def get_settings(self) -> StrategySettings:
        """Get strategy settings."""
        return self.settings


__all__ = ['DiscoveredStrategy']