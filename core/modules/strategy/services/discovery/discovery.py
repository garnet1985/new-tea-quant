#!/usr/bin/env python3
"""
Strategy discovery service.

职责：
- 递归发现 userspace/strategies 下策略目录
- 系统生成策略 ID（相对 strategies_root 的 POSIX 路径）
- 加载并校验 settings / worker
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.infra.project_context import ConfigManager, PathManager
from core.modules.strategy.engines.shared.data_classes.discovered_strategy import (
    DiscoveredStrategy,
)
from core.modules.strategy.engines.shared.data_classes.strategy_settings.settings_base import (
    SettingsBase,
)
from core.modules.strategy.engines.shared.data_classes.strategy_settings.strategy_settings import (
    StrategySettings,
)

from .path_rules import is_machine_readable_strategy_path, relative_strategy_key
from .worker_loader import load_strategy_worker_class

logger = logging.getLogger(__name__)


class StrategyDiscoveryHelper:
    """策略发现助手。"""

    @staticmethod
    def discover_strategies(
        strategies_root: Path = None,
    ) -> Dict[str, DiscoveredStrategy]:
        """发现所有可加载且校验通过的策略（enabled / disabled 均包含）。"""
        if strategies_root is None:
            strategies_root = PathManager.get_strategies_root()

        if not strategies_root.exists():
            logger.warning("策略目录不存在: %s", strategies_root)
            return {}

        discovered: Dict[str, DiscoveredStrategy] = {}
        for strategy_folder in StrategyDiscoveryHelper._iter_strategy_directories(strategies_root):
            strategy_info = StrategyDiscoveryHelper.load_strategy(
                strategy_folder,
                strategies_root=strategies_root,
            )
            if strategy_info:
                discovered[strategy_info.name] = strategy_info
                logger.info("发现策略: %s", strategy_info.name)
        return discovered

    @staticmethod
    def _iter_strategy_directories(strategies_root: Path) -> List[Path]:
        root = Path(strategies_root)
        candidates: List[Path] = []
        for dirpath, dirnames, _filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if not str(d).startswith("_")]
            folder = Path(dirpath)
            if (folder / "settings.py").is_file() and (folder / "strategy_worker.py").is_file():
                candidates.append(folder)
        candidates.sort(key=lambda p: relative_strategy_key(p, root))
        return candidates

    @staticmethod
    def load_strategy(
        strategy_folder: Path,
        *,
        strategies_root: Optional[Path] = None,
    ) -> Optional[DiscoveredStrategy]:
        """加载单个策略目录。"""
        folder = Path(strategy_folder)
        if strategies_root is None:
            strategies_root = PathManager.get_strategies_root()
        root = Path(strategies_root)

        try:
            strategy_key = relative_strategy_key(folder, root)
        except ValueError:
            logger.warning("策略目录不在 strategies_root 下: %s", folder)
            return None

        if not is_machine_readable_strategy_path(strategy_key):
            logger.warning(
                "策略路径含非 machine-readable 段，已跳过: %s（须为字母开头的 ASCII 字母/数字/下划线）",
                strategy_key,
            )
            return None

        settings_file = folder / "settings.py"
        if not settings_file.is_file():
            logger.warning("策略 %s 缺少 settings.py", strategy_key)
            return None

        try:
            settings_dict = ConfigManager.load_python(settings_file, var_name="settings")
        except Exception as exc:
            logger.error("加载 settings 失败: %s, error=%s", strategy_key, exc)
            return None

        if not isinstance(settings_dict, dict):
            logger.error("策略 %s 的 settings 不是 dict", strategy_key)
            return None

        worker_loaded = load_strategy_worker_class(folder, strategy_key)
        if not worker_loaded:
            logger.warning("策略 %s 无法加载 strategy_worker.py", strategy_key)
            return None
        worker_module_path, worker_class_name, worker_file_path, worker_class = worker_loaded

        settings = StrategySettings(raw_settings=dict(settings_dict))
        validation = settings.validate()
        if not validation.is_usable():
            logger.error("策略 %s settings 验证失败", strategy_key)
            for err in validation.errors:
                if err.get("level") == SettingsBase.LEVEL_CRITICAL:
                    logger.error("  [%s] %s", err.get("field_path"), err.get("message"))
            return None
        validation.log_warnings(logger)

        discovered = DiscoveredStrategy(
            name=strategy_key,
            folder=folder.resolve(),
            worker_class=worker_class,
            worker_module_path=worker_module_path,
            worker_class_name=worker_class_name,
            worker_file_path=worker_file_path,
            settings=settings,
        )
        discovered.validate_required_fields()
        return discovered

    @staticmethod
    def validate_settings(settings_dict: Dict[str, Any]) -> bool:
        """校验 settings 有效性（供外部调用）。"""
        if not isinstance(settings_dict, dict):
            logger.error("settings 必须是字典")
            return False
        settings = StrategySettings(raw_settings=dict(settings_dict))
        return settings.validate().is_usable()


__all__ = ["StrategyDiscoveryHelper"]
