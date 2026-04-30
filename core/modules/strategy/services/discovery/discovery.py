#!/usr/bin/env python3
"""
Strategy discovery service.

职责：
- 发现用户策略
- 加载策略配置
- 验证策略有效性（``StrategySettings.validate()``）
"""

from __future__ import annotations

import importlib
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from core.infra.project_context import PathManager
from core.modules.strategy.base_strategy_worker import BaseStrategyWorker
from core.modules.strategy.engines.shared.data_classes.discovered_strategy import (
    DiscoveredStrategy,
)
from core.modules.strategy.engines.shared.data_classes.strategy_settings.settings_base import (
    SettingsBase,
)
from core.modules.strategy.engines.shared.data_classes.strategy_settings.strategy_settings import (
    StrategySettings,
)

logger = logging.getLogger(__name__)


class StrategyDiscoveryHelper:
    """策略发现助手。"""

    @staticmethod
    def discover_strategies(
        strategies_root: Path = None,
    ) -> Dict[str, DiscoveredStrategy]:
        """发现所有用户策略（包含 enabled 与 disabled，但必须可加载且可校验）。"""
        if strategies_root is None:
            strategies_root = PathManager.userspace() / "strategies"

        if not strategies_root.exists():
            logger.warning("策略目录不存在: %s", strategies_root)
            return {}

        discovered: Dict[str, DiscoveredStrategy] = {}
        for strategy_folder in strategies_root.iterdir():
            if not strategy_folder.is_dir() or strategy_folder.name.startswith("_"):
                continue
            strategy_info = StrategyDiscoveryHelper.load_strategy(strategy_folder)
            if strategy_info:
                discovered[strategy_info.name] = strategy_info
                logger.info("发现策略: %s", strategy_info.name)
        return discovered

    @staticmethod
    def load_strategy(strategy_folder: Path) -> Optional[DiscoveredStrategy]:
        """加载单个策略并返回结构化策略信息。"""
        strategy_name = strategy_folder.name

        settings_file = strategy_folder / "settings.py"
        if not settings_file.exists():
            logger.warning("策略 %s 缺少 settings.py", strategy_name)
            return None

        settings_module_path = f"userspace.strategies.{strategy_name}.settings"
        try:
            settings_module = importlib.import_module(settings_module_path)
            settings_dict = getattr(settings_module, "settings")
        except Exception as exc:
            logger.error("加载 settings 失败: %s, error=%s", strategy_name, exc)
            return None

        if not isinstance(settings_dict, dict):
            logger.error("策略 %s 的 settings 不是 dict", strategy_name)
            return None

        worker_file = strategy_folder / "strategy_worker.py"
        if not worker_file.exists():
            logger.warning("策略 %s 缺少 strategy_worker.py", strategy_name)
            return None

        worker_module_path = f"userspace.strategies.{strategy_name}.strategy_worker"
        try:
            worker_module = importlib.import_module(worker_module_path)
            worker_class = None
            for attr_name in dir(worker_module):
                attr = getattr(worker_module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, BaseStrategyWorker)
                    and attr is not BaseStrategyWorker
                ):
                    worker_class = attr
                    break
            if not worker_class:
                logger.warning("策略 %s 没有找到 Worker 类", strategy_name)
                return None
        except Exception as exc:
            logger.error("加载 worker 失败: %s, error=%s", strategy_name, exc)
            return None

        settings = StrategySettings(raw_settings=dict(settings_dict))
        validation = settings.validate()
        if not validation.is_usable():
            logger.error("策略 %s settings 验证失败", strategy_name)
            for err in validation.errors:
                if err.get("level") == SettingsBase.LEVEL_CRITICAL:
                    logger.error("  [%s] %s", err.get("field_path"), err.get("message"))
            return None
        validation.log_warnings(logger)

        discovered = DiscoveredStrategy(
            name=strategy_name,
            folder=strategy_folder,
            worker_class=worker_class,
            worker_module_path=worker_module_path,
            worker_class_name=worker_class.__name__,
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

