#!/usr/bin/env python3
"""
策略管理器 - 统一管理所有策略的初始化、注册和调度
"""
from typing import Dict, List, Any, Type
from loguru import logger
from utils.db.db_manager import DatabaseManager
from .libs.base_strategy import BaseStrategy
import importlib
from pathlib import Path
import os



class Analyzer:
    """策略管理器 - 统一管理所有策略"""
    
    def __init__(self, connected_db: DatabaseManager, is_verbose: bool = False):
        """
        初始化策略管理器
        
        Args:
            db_manager: 已初始化的数据库管理器实例
        """
        self.db = connected_db
        self.is_verbose = is_verbose

        # grab all existing strategies no matter if they are enabled or not
        self._strategies = []
        # cache all enabled strategy instances
        self.ins = {}
        
    def initialize(self):
        """初始化策略管理器"""
        # 第一阶段：注册所有策略
        self._register_all_strategies()

        # 第二阶段：初始化启用的策略
        self._initialize_enabled_strategies()

    def register_strategy(self, strategy_class: Type[BaseStrategy]):
        self._strategies.append(strategy_class)
    
    
    def _register_all_strategies(self) -> None:
        """注册所有策略（不检查启用状态）"""
        strategy_dir = Path(__file__).parent / "strategy"
        
        if not strategy_dir.exists():
            logger.warning(f"策略目录不存在: {strategy_dir}")
            return
        
        # 遍历策略文件夹
        for strategy_folder in strategy_dir.iterdir():
            if not strategy_folder.is_dir() or strategy_folder.name.startswith('_'):
                continue
                
            # 检查是否存在 strategy.py 文件
            strategy_file = strategy_folder / "strategy.py"
            
            if not strategy_file.exists():
                if self.is_verbose:
                    logger.info(f"跳过 {strategy_folder.name}: 未找到 strategy.py 文件")
                continue
            
            # 尝试导入策略模块
            try:
                module_path = f"app.analyzer.strategy.{strategy_folder.name}.strategy"
                strategy_module = importlib.import_module(module_path)
                
                # 查找继承 BaseStrategy 的策略类
                strategy_class = None
                for attr_name in dir(strategy_module):
                    attr = getattr(strategy_module, attr_name)
                    if (isinstance(attr, type) and 
                        issubclass(attr, BaseStrategy) and 
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
                
                self.register_strategy(strategy_class)
                        
            except ImportError as e:
                logger.warning(f"⚠️ 导入策略模块 {strategy_folder.name} 失败: {e}")
            except Exception as e:
                logger.error(f"❌ 注册策略失败: {e}")
    
    def _initialize_enabled_strategies(self) -> None:
        """初始化所有启用的策略"""
        for strategy_class in self._strategies:
            # 检查策略是否启用
            if strategy_class.is_enabled:
                # 先创建策略实例（不调用initialize）
                strategy_instance = strategy_class(db=self.db, is_verbose=self.is_verbose)
                
                # 现在调用策略的初始化方法
                strategy_instance.initialize()
                
                # 注册策略的表到数据库管理器
                self._register_strategy_tables(strategy_instance)
                
                # 创建所有注册的表
                self.db.create_tables()
                
                self.ins[strategy_instance.get_abbr()] = strategy_instance
            else:
                logger.info(f"跳过 {strategy_class.__name__}: 策略已禁用")
    

    def _register_strategy_tables(self, strategy_instance: BaseStrategy) -> None:
        """注册策略的表到数据库管理器"""
        try:
            if hasattr(strategy_instance, 'required_tables'):
                for table_name, table_model in strategy_instance.required_tables.items():
                    # 跳过基础表，只注册策略特有的表
                    if hasattr(table_model, 'is_base_table') and table_model.is_base_table:
                        continue
                    
                    # 获取表的前缀（从策略实例获取）
                    abbreviation = strategy_instance.abbreviation
                    
                    # 获取表的 schema 文件路径
                    schema_path = table_model.schema_path if hasattr(table_model, 'schema_path') else None
                    
                    # 注册表到数据库管理器
                    self.db.register_table(
                        table_name=table_name,
                        prefix=abbreviation,
                        schema=schema_path,
                        model_class=type(table_model)
                    )
        except Exception as e:
            logger.error(f"注册策略表失败: {e}")
    
    def get_strategy(self, strategy_key: str) -> BaseStrategy:
        """
        获取策略实例
        
        Args:
            strategy_key: 策略标识符
            
        Returns:
            BaseStrategy: 策略实例
        """
        if strategy_key not in self.ins:
            raise KeyError(f"策略 {strategy_key} 未找到，请确保已初始化")
        
        return self.ins[strategy_key]
    
    def get_all_strategies(self) -> Dict[str, BaseStrategy]:
        """获取所有策略实例"""
        return self.ins.copy()
    
    def get_strategy_info(self) -> List[Dict[str, Any]]:
        """获取所有策略的信息"""
        return [
            {
                'key': key,
                'info': strategy.get_strategy_info()
            }
            for key, strategy in self.ins.items()
        ]
    
    def scan(self) -> Dict[str, List[Dict[str, Any]]]:
        results = {}
        for key, strategy in self.ins.items():
            results[key] = strategy.scan()
        return results

    def simulate(self):
        for key, strategy in self.ins.items():
            strategy.simulate()