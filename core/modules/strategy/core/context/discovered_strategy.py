"""Layer 1：策略发现结果（runnable 最小集）。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Type

from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import StrategySettings
from core.modules.strategy.core.engines.shared.services.strategy_settings.validation_report import ValidationReport


@dataclass
class DiscoveredStrategy:
    """Discovery 产物：文件、key、hooks 模块信息齐全且校验通过即可 run。

    id 信息
    -------
    key
        ``settings.meta.key``，全局唯一
    id
        策略在 strategies 根下的相对路径（location id）

    位置信息
    --------
    strategies_root, folder, strategy_file, settings_file

    模块信息
    --------
    worker_class, worker_module_path, worker_class_name, worker_file_path
    """

    key: str
    id: str
    strategies_root: Path
    folder: Path
    strategy_file: Path
    settings_file: Path
    settings: StrategySettings
    worker_class: Type[Any]
    worker_module_path: str
    worker_class_name: str
    worker_file_path: Path

    @property
    def name(self) -> str:
        """Deprecated alias for ``id``."""
        return self.id

    @property
    def disk_settings(self) -> Dict[str, Any]:
        return self.settings.raw_settings

    @property
    def worker_ref(self) -> Dict[str, str]:
        return {
            "worker_module_path": self.worker_module_path,
            "worker_class_name": self.worker_class_name,
            "worker_file_path": str(self.worker_file_path),
        }

    @classmethod
    def from_info(
        cls,
        info: Dict[str, Any],
        *,
        strategies_root: Path,
    ) -> DiscoveredStrategy:
        folder = Path(info["folder"])
        discovered = cls(
            key=str(info["key"]),
            id=str(info["name"]),
            strategies_root=strategies_root,
            folder=folder,
            strategy_file=folder / "strategy.py",
            settings_file=folder / "settings.py",
            settings=StrategySettings(raw_settings=dict(info["settings"])),
            worker_class=info["worker_class"],
            worker_module_path=str(info["worker_module_path"]),
            worker_class_name=str(info["worker_class_name"]),
            worker_file_path=Path(info["worker_file_path"]),
        )
        discovered.validate()
        return discovered

    def validate_files(self) -> None:
        if not self.folder.is_dir():
            raise ValueError(f"策略目录不存在: {self.folder}")
        if not self.strategy_file.is_file():
            raise ValueError(f"缺少 strategy.py: {self.strategy_file}")
        if not self.settings_file.is_file():
            raise ValueError(f"缺少 settings.py: {self.settings_file}")

    def validate_key(self) -> None:
        if not str(self.key).strip():
            raise ValueError("settings.meta.key 不能为空")

    def validate_hooks(self) -> None:
        from core.modules.strategy.core.hooks.base import StrategyHooks

        if not issubclass(self.worker_class, StrategyHooks):
            raise ValueError(
                f"{self.worker_class_name} 须继承 {StrategyHooks.__name__}"
            )

    def validate_settings(self) -> ValidationReport:
        return self.settings.validate()

    def validate(self) -> ValidationReport:
        """settings.py + strategy.py + meta.key + hooks 继承。"""
        self.validate_files()
        self.validate_key()
        self.validate_hooks()
        return self.validate_settings()


__all__ = ["DiscoveredStrategy"]
