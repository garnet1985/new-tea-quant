#!/usr/bin/env python3
"""
策略管理器 - 统一管理所有策略的初始化、注册和调度
"""
from typing import Dict, List, Any, Type
from loguru import logger
from utils.db.db_manager import DatabaseManager
from .components.base_strategy import BaseStrategy
from .components.settings_validator import SettingsValidator
import importlib
from pathlib import Path
import os



class Analyzer:
    """策略管理器 - 统一管理所有策略"""
    
    def __init__(self, connected_db: DatabaseManager = None, is_verbose: bool = False):
        """
        初始化策略管理器
        
        Args:
            connected_db: 已初始化的数据库管理器实例（可选，如果不提供则使用全局实例）
            is_verbose: 是否启用详细日志
        """

        self.db = connected_db
        self.is_verbose = is_verbose

        # grab all existing strategies no matter if they are enabled or not
        self.all_strategies = []

        # cache all enabled strategy instances
        self.enabled_strategies = {}
        
        # 初始化设置验证器
        self.settings_validator = SettingsValidator()
        
    def initialize(self):
        """初始化策略管理器"""
        # 第一阶段：注册所有策略
        self._register_all_strategies()

        # 第二阶段：初始化启用的策略
        self._initialize_enabled_strategies()

    
    def _register_all_strategies(self) -> None:
        """注册所有策略（不检查启用状态）"""
        strategy_dir = Path(__file__).parent / "strategy"
        
        if not strategy_dir.exists():
            logger.warning(f"策略目录不存在: {strategy_dir}")
            return
        
        # 遍历策略文件夹（仅第一级目录）
        for strategy_folder in strategy_dir.iterdir():
            if not strategy_folder.is_dir() or strategy_folder.name.startswith('_'):
                continue
                
            # 入口文件应与文件夹同名，如 HL/HL.py, historicLow/historicLow.py
            entry_file = strategy_folder / f"{strategy_folder.name}.py"
            
            if not entry_file.exists():
                if self.is_verbose:
                    logger.info(f"跳过 {strategy_folder.name}: 未找到入口文件 {strategy_folder.name}.py")
                continue
            
            # 尝试导入策略模块
            try:
                module_path = f"app.analyzer.strategy.{strategy_folder.name}.{strategy_folder.name}"
                strategy_module = importlib.import_module(module_path)
                
                # 查找继承 BaseStrategy 的策略类
                strategy_class = None
                for attr_name in dir(strategy_module):
                    attr = getattr(strategy_module, attr_name)
                    if (isinstance(attr, type) and 
                        hasattr(attr, '__bases__') and
                        any(base.__name__ == 'BaseStrategy' for base in attr.__bases__) and 
                        attr != BaseStrategy):
                        strategy_class = attr
                        break
                
                if strategy_class is None:
                    if self.is_verbose:
                        logger.warning(f"跳过 {strategy_folder.name}: 未找到继承 BaseStrategy 的策略类")
                    continue

                if not hasattr(strategy_class, 'is_enabled'):
                    logger.warning(f"跳过 {strategy_folder.name}: 未找到 is_enabled 属性")
                    continue
                
                self.all_strategies.append(strategy_class)
                        
            except ImportError as e:
                logger.warning(f"⚠️ 导入策略模块 {strategy_folder.name} 失败: {e}")
            except Exception as e:
                logger.error(f"❌ 注册策略失败: {e}")
    
    def _initialize_enabled_strategies(self) -> None:
        """初始化所有启用的策略"""
        failed_strategies = []  # 记录验证失败的策略
        
        for strategy_class in self.all_strategies:
            # 检查策略是否启用

            if strategy_class.is_enabled:
                
                try:
                    # 创建策略实例
                    strategy_instance = strategy_class(db=self.db, is_verbose=self.is_verbose)

                    is_valid, validated_settings = self.settings_validator.validate_settings(strategy_instance.settings, strategy_class.__name__)
                    
                    if not is_valid:
                        logger.error(f"❌ 策略 {strategy_class.__name__} 设置验证失败: {strategy_instance.settings}")
                        logger.error(f"   策略 {strategy_class.__name__} 将被跳过，不会参与后续运行")
                        continue
                    
                    strategy_instance.settings = validated_settings

                    # 初始化策略（策略自己负责表的注册和创建）
                    strategy_instance.initialize()
                    
                    self.enabled_strategies[strategy_instance.get_abbr()] = strategy_instance
                    
                    if self.is_verbose:
                        logger.info(f"✅ 策略 {strategy_instance.name} 初始化成功")
                        
                except ValueError as e:
                    # Settings验证失败
                    failed_strategies.append(strategy_class.__name__)
                    logger.error(f"❌ 策略 {strategy_class.__name__} 设置验证失败: {e}")
                    logger.error(f"   策略 {strategy_class.__name__} 将被跳过，不会参与后续运行")
                    
            else:
                logger.info(f"跳过 {strategy_class.__name__}: 策略已禁用")
        
        # 如果有策略验证失败，明确告知用户
        if failed_strategies:
            logger.error(f"⚠️  以下策略因设置验证失败或初始化错误被跳过: {', '.join(failed_strategies)}")
            logger.error(f"   请检查这些策略的设置文件，修正错误后重新运行")
            
            # 如果没有策略成功初始化，抛出异常阻止程序继续运行
            if not self.enabled_strategies:
                error_msg = "❌ 所有启用的策略都初始化失败，程序无法继续运行"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

    def scan(self) -> Dict[str, List[Dict[str, Any]]]:
        """扫描所有策略的投资机会"""
        results = {}
        for key, strategy in self.enabled_strategies.items():
            results[key] = strategy.scan()
        return results

    def simulate(self):
        for key, strategy in self.enabled_strategies.items():
            strategy.simulate()
