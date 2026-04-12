#!/usr/bin/env python3
"""
Strategy Discovery Helper - 策略发现和管理

职责：
- 发现用户策略
- 加载策略配置
- 验证策略有效性（``StrategySettings.validate_base_settings``）
"""

from typing import Dict, Any, Optional
from pathlib import Path
import logging
import importlib

from core.infra.project_context import PathManager
from core.modules.strategy.data_classes.strategy_info import StrategyInfo
from core.modules.strategy.data_classes.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.data_classes.strategy_settings.settings_base import SettingsBase

logger = logging.getLogger(__name__)


class StrategyDiscoveryHelper:
    """策略发现助手"""
    
    @staticmethod
    def discover_strategies(strategies_root: Path = None) -> Dict[str, StrategyInfo]:
        """
        发现所有用户策略
        
        Args:
            strategies_root: 策略根目录（默认使用 PathManager.userspace() / "strategies"）
        
        Returns:
            strategy_cache: {strategy_name: StrategyInfo}
        """
        if strategies_root is None:
            strategies_root = PathManager.userspace() / "strategies"
        
        if not strategies_root.exists():
            logger.warning(f"策略目录不存在: {strategies_root}")
            return {}
        
        strategy_cache: Dict[str, StrategyInfo] = {}
        
        # 遍历策略文件夹
        for strategy_folder in strategies_root.iterdir():
            if not strategy_folder.is_dir() or strategy_folder.name.startswith('_'):
                continue
            
            # 加载策略
            strategy_info = StrategyDiscoveryHelper.load_strategy(strategy_folder)
            if strategy_info:
                strategy_cache[strategy_info.name] = strategy_info
                logger.info(f"✅ 发现策略: {strategy_info.name}")
        
        return strategy_cache
    
    @staticmethod
    def load_strategy(strategy_folder: Path) -> Optional[StrategyInfo]:
        """
        加载单个策略
        
        Args:
            strategy_folder: 策略文件夹路径
        
        Returns:
            StrategyInfo（settings 为已校验的 ``StrategySettings``）
        """
        strategy_name = strategy_folder.name
        
        # 1. 加载 settings.py
        settings_file = strategy_folder / "settings.py"
        if not settings_file.exists():
            logger.warning(f"策略 {strategy_name} 缺少 settings.py")
            return None
        
        # 动态导入 settings
        settings_module_path = f"userspace.strategies.{strategy_name}.settings"
        try:
            settings_module = importlib.import_module(settings_module_path)
            settings_dict = getattr(settings_module, 'settings')
        except Exception as e:
            logger.error(f"加载 settings 失败: {strategy_name}, error={e}")
            return None
        
        if not isinstance(settings_dict, dict):
            logger.error(f"策略 {strategy_name} 的 settings 不是 dict")
            return None
        
        # 2. 加载 strategy_worker.py
        worker_file = strategy_folder / "strategy_worker.py"
        if not worker_file.exists():
            logger.warning(f"策略 {strategy_name} 缺少 strategy_worker.py")
            return None
        
        # 动态导入 worker class
        worker_module_path = f"userspace.strategies.{strategy_name}.strategy_worker"
        try:
            worker_module = importlib.import_module(worker_module_path)
            
            # 找到 BaseStrategyWorker 的子类
            from core.modules.strategy.base_strategy_worker import BaseStrategyWorker
            worker_class = None
            for attr_name in dir(worker_module):
                attr = getattr(worker_module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, BaseStrategyWorker) and 
                    attr is not BaseStrategyWorker):
                    worker_class = attr
                    break
            
            if not worker_class:
                logger.warning(f"策略 {strategy_name} 没有找到 Worker 类")
                return None
        
        except Exception as e:
            logger.error(f"加载 worker 失败: {strategy_name}, error={e}")
            return None
        
        # 3. 数据类校验 settings（替代原 component 内校验）
        settings = StrategySettings(raw_settings=dict(settings_dict))
        validation = settings.validate_base_settings()
        if not validation.is_usable():
            logger.error(f"策略 {strategy_name} settings 验证失败")
            for err in validation.errors:
                if err.get("level") == SettingsBase.LEVEL_CRITICAL:
                    logger.error("  [%s] %s", err.get("field_path"), err.get("message"))
            return None
        validation.log_warnings(logger)
        
        return StrategyInfo(
            name=strategy_name,
            folder=strategy_folder,
            worker_class=worker_class,
            worker_module_path=worker_module_path,
            worker_class_name=worker_class.__name__,
            settings=settings,
        )
    
    @staticmethod
    def validate_settings(settings_dict: Dict[str, Any]) -> bool:
        """
        验证 settings 有效性（供外部工具调用；逻辑与加载策略时一致）。
        """
        if not isinstance(settings_dict, dict):
            logger.error("settings 必须是字典")
            return False
        bs = StrategySettings(raw_settings=dict(settings_dict))
        r = bs.validate_base_settings()
        return r.is_usable()
