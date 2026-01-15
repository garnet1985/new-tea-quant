#!/usr/bin/env python3
"""
Strategy Discovery Helper - 策略发现和管理

职责：
- 发现用户策略
- 加载策略配置
- 验证策略有效性
"""

from typing import Dict, Any, Optional
from pathlib import Path
import logging
import importlib

from core.infra.project_context import PathManager

logger = logging.getLogger(__name__)


class StrategyDiscoveryHelper:
    """策略发现助手"""
    
    @staticmethod
    def discover_strategies(strategies_root: Path = None) -> Dict[str, Dict[str, Any]]:
        """
        发现所有用户策略
        
        Args:
            strategies_root: 策略根目录（默认使用 PathManager.userspace() / "strategies"）
        
        Returns:
            strategy_cache: {strategy_name: strategy_info}
        """
        if strategies_root is None:
            strategies_root = PathManager.userspace() / "strategies"
        
        if not strategies_root.exists():
            logger.warning(f"策略目录不存在: {strategies_root}")
            return {}
        
        strategy_cache = {}
        
        # 遍历策略文件夹
        for strategy_folder in strategies_root.iterdir():
            if not strategy_folder.is_dir() or strategy_folder.name.startswith('_'):
                continue
            
            # 加载策略
            strategy_info = StrategyDiscoveryHelper.load_strategy(strategy_folder)
            if strategy_info:
                strategy_name = strategy_info['name']
                strategy_cache[strategy_name] = strategy_info
                logger.info(f"✅ 发现策略: {strategy_name}")
        
        return strategy_cache
    
    @staticmethod
    def load_strategy(strategy_folder: Path) -> Optional[Dict[str, Any]]:
        """
        加载单个策略
        
        Args:
            strategy_folder: 策略文件夹路径
        
        Returns:
            strategy_info: {
                'name': 'momentum',
                'folder': Path(...),
                'worker_class': MomentumStrategyWorker,
                'worker_module_path': 'userspace.strategies.momentum.strategy_worker',
                'worker_class_name': 'MomentumStrategyWorker',
                'settings': StrategySettings(...)
            }
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
        
        # 3. 验证 settings
        if not StrategyDiscoveryHelper.validate_settings(settings_dict):
            logger.error(f"策略 {strategy_name} settings 验证失败")
            return None
        
        # 4. 创建 StrategySettings 对象
        from core.modules.strategy.models.strategy_settings import StrategySettings
        settings = StrategySettings(settings_dict)
        
        # 5. 返回策略信息
        return {
            'name': strategy_name,
            'folder': strategy_folder,
            'worker_class': worker_class,
            'worker_module_path': worker_module_path,
            'worker_class_name': worker_class.__name__,
            'settings': settings
        }
    
    @staticmethod
    def validate_settings(settings_dict: Dict[str, Any]) -> bool:
        """
        验证 settings 有效性（新格式）
        
        必须包含：
        - name: str
        - data: dict（新格式，替代旧的 klines）
        """
        if not isinstance(settings_dict, dict):
            logger.error("settings 必须是字典")
            return False
        
        # 新格式：必须包含 name 和 data
        required_keys = ['name', 'data']
        for key in required_keys:
            if key not in settings_dict:
                logger.error(f"settings 缺少必需字段: {key}")
                return False
        
        # 验证 data 字段的必要子字段
        data = settings_dict.get('data', {})
        if not isinstance(data, dict):
            logger.error("settings.data 必须是字典")
            return False
        
        # 兼容两种命名方式：
        # - 旧版：base / adjust
        # - 新版：base_price_source / adjust_type
        has_base = ('base' in data) or ('base_price_source' in data)
        has_adjust = ('adjust' in data) or ('adjust_type' in data)
        
        if not has_base:
            logger.error("settings.data.base 不能为空（或缺少 base_price_source）")
            return False
        
        if not has_adjust:
            logger.error("settings.data.adjust 不能为空（或缺少 adjust_type）")
            return False
        
        return True
