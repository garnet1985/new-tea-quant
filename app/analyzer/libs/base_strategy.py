#!/usr/bin/env python3
"""
策略基类 - 定义所有策略的通用接口和基础功能
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from loguru import logger
from utils.db.db_manager import DatabaseManager


class BaseStrategy(ABC):
    """策略基类 - 所有策略必须继承此类"""
    
    def __init__(self, db: DatabaseManager, is_verbose: bool = False, name: str = None, description: str = None, prefix: str = None):
        """
        初始化策略基类
        
        Args:
            db_manager: 已初始化的数据库管理器实例
            strategy_name: 策略名称
            strategy_prefix: 策略前缀（用于表名）
        """
        self.db = db
        self.is_verbose = is_verbose
        self.is_enabled = True

        self.name = name
        self.description = description
        self.prefix = prefix
        
        # 策略所需的表模型
        self.required_tables: Dict[str, Any] = {}
        
        # 初始化策略
        self._check_required_fields()

    def set_verbose(self, is_verbose: bool):
        """设置是否打印日志"""
        self.is_verbose = is_verbose
    
    
    def _check_required_fields(self):
        """检查策略所需的必要字段"""
        if self.name is None:
            raise ValueError("strategy require a name.")

        if self.prefix is None:
            raise ValueError("strategy require a prefix.")

        if self.is_verbose:
            logger.info(f"🔧 初始化策略: {self.name}")
    
    def initialize(self):
        pass
    

    @abstractmethod
    def scan(self) -> List[Dict[str, Any]]:
        """
        扫描投资机会 - 抽象方法，子类必须实现
        
        Returns:
            List[Dict]: 投资机会列表
        """
        pass
    
    @abstractmethod
    def report(self, opportunities: List[Dict[str, Any]]) -> None:
        """
        呈现扫描结果 - 抽象方法，子类必须实现
        
        Args:
            opportunities: 投资机会列表
        """
        pass
    
    @abstractmethod
    def test(self) -> None:
        """
        测试策略 - 使用历史数据模拟策略 - 抽象方法，子类必须实现
        """
        pass