#!/usr/bin/env python3
"""
策略执行器 - 使用组件架构封装多进程扫描和模拟逻辑
"""
from typing import Dict, List, Any, Optional
from loguru import logger
from .data_loader import DataLoader
from .scan_executor import ScanExecutor
from utils.db.db_manager import DatabaseManager


class StrategyExecutor:
    """策略执行器 - 使用组件架构封装多进程逻辑"""
    
    def __init__(self, strategy):
        """
        初始化策略执行器
        
        Args:
            strategy: 策略实例
        """
        self.strategy = strategy
        self.db = strategy.db
        self.is_verbose = strategy.is_verbose
        
        # 初始化组件 - 使用连接池的DatabaseManager
        db = DatabaseManager(use_connection_pool=True, is_verbose=True)
        db.initialize()
        self.data_loader = DataLoader(db)
        self.scan_executor = ScanExecutor(strategy, db, self.is_verbose)
    
    def scan_all_stocks(self, settings: Dict[str, Any], 
                       max_workers: Optional[int] = None,
                       batch_size: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        扫描所有股票的投资机会 - 使用ScanExecutor组件
        
        Args:
            settings: 策略设置
            max_workers: 最大并行进程数，None时使用CPU核心数
            batch_size: Batch模式下的batch大小，None时使用CPU核心数
            
        Returns:
            List[Dict]: 所有发现的投资机会列表
        """
        return self.scan_executor.scan_all_stocks(settings, max_workers, batch_size)
    
    def scan_single_stock(self, stock_id: str, settings: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        扫描单只股票
        
        Args:
            stock_id: 股票ID
            settings: 策略设置
            
        Returns:
            Optional[Dict]: 投资机会，如果没有则返回None
        """
        # 加载数据
        stock_data = self.data_loader.load_stock_data(stock_id, settings, self.strategy.name)
        
        # 获取基础周期数据
        kline_config = settings.get('klines', {})
        base_term = kline_config.get('base_term', 'daily')
        daily_k_lines = stock_data.get(base_term, [])
        
        if not daily_k_lines:
            return None
        
        # 扫描最后一天的机会
        return self.strategy.scan_opportunity(stock_id, daily_k_lines)
