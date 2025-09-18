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
    def scan_opportunity(self, stock_id: str, data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        扫描单只股票的投资机会 - 抽象方法，子类必须实现
        
        Args:
            stock_id: 股票ID
            data: 股票的历史K线数据（到当前日期为止）
            
        Returns:
            Optional[Dict]: 如果发现投资机会则返回机会字典，否则返回None
        """
        pass
    
    def get_validated_settings(self) -> Dict[str, Any]:
        """
        获取验证后的设置
        
        Returns:
            Dict: 验证后的设置
        """
        if hasattr(self, '_validated_settings'):
            return self._validated_settings
        
        # 如果没有验证后的设置，返回原始设置
        return getattr(self, 'strategy_settings', None) or getattr(self, 'settings', {})
    
    def scan(self, settings: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        扫描所有股票的投资机会 - 框架方法，内部使用多进程
        用户不需要复写此方法，只需要实现 scan_opportunity 方法
        
        Args:
            settings: 策略设置，如果为None则使用策略的默认设置
            
        Returns:
            List[Dict]: 所有发现的投资机会列表
        """
        from .strategy_executor import StrategyExecutor
        
        executor = StrategyExecutor(self)
        
        # 使用传入的settings或策略的验证后设置
        if settings is None:
            settings = self.get_validated_settings()
        
        return executor.scan_all_stocks(settings)
    
    @abstractmethod
    def report(self, opportunities: List[Dict[str, Any]]) -> None:
        """
        呈现扫描结果 - 抽象方法，子类必须实现
        
        Args:
            opportunities: 投资机会列表
        """
        pass
    
    def simulate(self) -> Dict[str, Any]:
        """
        模拟策略 - 使用历史数据模拟策略
        用户不需要复写此方法，只需要实现 simulate_one_day 方法
        
        Returns:
            Dict[str, Any]: 模拟结果
        """
        from .simulator.simulator import Simulator
        
        simulator = Simulator()
        
        # 获取策略设置
        settings = self.get_validated_settings()
        
        # 运行模拟 - 使用用户定义的 simulate_one_day 方法
        result = simulator.run(
            settings=settings,
            on_simulate_one_day=self.simulate_one_day,
            on_single_stock_summary=self.stock_summary,
            on_simulate_complete=None
        )
        
        return result
    
    @abstractmethod
    def simulate_one_day(self, stock_id: str, current_date: str, current_record: Dict[str, Any], 
                        historical_data: List[Dict[str, Any]], current_investment: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        模拟单日交易逻辑 - 抽象方法，子类必须实现
        
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
        pass
    
    @abstractmethod
    def stock_summary(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        单只股票模拟结果汇总 - 抽象方法，子类必须实现
        
        Args:
            result: 单只股票的模拟结果（包含 investments/settled_investments）
            
        Returns:
            Dict: 追加到默认summary的track（可以返回空字典）
        """
        pass
    