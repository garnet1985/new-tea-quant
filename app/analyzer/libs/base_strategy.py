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
    
    def __init__(self, db: DatabaseManager, is_verbose: bool = False, name: str = None, description: str = None, abbreviation: str = None):
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
        self.abbreviation = abbreviation
        
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

        if self.abbreviation is None:
            raise ValueError("strategy require a abbreviation. abbreviation is used to identify the strategy, it should be unique and machine readable.")

        if self.is_verbose:
            logger.info(f"🔧 初始化策略: {self.name}")
    
    def initialize(self):
        pass
    
    def get_abbr(self) -> str:
        """获取策略的缩写"""
        return self.abbreviation

    def get_strategy_info(self) -> Dict[str, Any]:
        """
        获取策略信息 - 子类可以重写此方法
        
        Returns:
            Dict: 策略信息字典
        """
        return {
            'name': self.name,
            'description': self.description,
            'abbreviation': self.abbreviation,
            'is_enabled': self.is_enabled
        }

    @abstractmethod
    async def scan(self) -> List[Dict[str, Any]]:
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
    def simulate(self) -> None:
        """
        模拟策略 - 使用历史数据模拟策略 - 抽象方法，子类必须实现
        """
        pass
    
    @staticmethod
    def simulate_single_day(stock_id: str, current_date: str, current_record: Dict[str, Any], 
                           historical_data: List[Dict[str, Any]], current_investment: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        模拟单日交易逻辑 - 子类可以重写此方法
        
        Args:
            stock_id: 股票ID
            current_date: 当前日期
            current_record: 当前日K线数据
            historical_data: 历史数据（到当前日之前）
            current_investment: 当前投资状态
            
        Returns:
            Dict[str, Any]: 包含以下字段的结果
                - new_investment: 新的投资（如果有）
                - settled_investments: 结算的投资列表
                - current_investment: 更新后的当前投资状态
        """
        # 默认实现：返回空结果，子类可以重写
        return {
            'new_investment': None,
            'settled_investments': [],
            'current_investment': current_investment
        }