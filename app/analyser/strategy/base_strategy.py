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
    
    def __init__(self, db: DatabaseManager, strategy_name: str, strategy_prefix: str, is_verbose: bool = False):
        """
        初始化策略基类
        
        Args:
            db_manager: 已初始化的数据库管理器实例
            strategy_name: 策略名称
            strategy_prefix: 策略前缀（用于表名）
        """
        self.db = db
        self.strategy_name = strategy_name
        self.strategy_prefix = strategy_prefix
        self.is_verbose = is_verbose
        
        # 策略所需的表模型
        self.required_tables: Dict[str, Any] = {}
        
        # 初始化策略
        self._initialize_strategy()

    def set_verbose(self, is_verbose: bool):
        """设置是否打印日志"""
        self.is_verbose = is_verbose
    
    def _initialize_strategy(self):
        """初始化策略 - 子类可以重写此方法"""
        if self.is_verbose:
            logger.info(f"🔧 初始化策略: {self.strategy_name}")
    
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
    
    def get_table(self, table_name: str):
        """获取策略表实例"""
        return self.required_tables.get(table_name)
    
    def log_info(self, message: str):
        """条件日志输出 - INFO级别"""
        if self.is_verbose:
            logger.info(f"[{self.strategy_name}] {message}")
    
    def log_debug(self, message: str):
        """条件日志输出 - DEBUG级别"""
        if self.is_verbose:
            logger.debug(f"[{self.strategy_name}] {message}")
    
    def log_warning(self, message: str):
        """警告日志输出 - 不受verbose控制"""
        logger.warning(f"[{self.strategy_name}] {message}")
    
    def log_error(self, message: str):
        """错误日志输出 - 不受verbose控制"""
        logger.error(f"[{self.strategy_name}] {message}")
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """获取策略信息"""
        return {
            'name': self.strategy_name,
            'prefix': self.strategy_prefix,
            'tables': list(self.required_tables.keys()),
            'description': getattr(self, 'strategy_description', '')
        }