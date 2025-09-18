#!/usr/bin/env python3
"""
数据加载器组件 - 根据策略设置加载和准备数据
"""
from typing import Dict, List, Any, Optional
from loguru import logger
from utils.db.db_manager import DatabaseManager


class DataLoader:
    """数据加载器 - 根据策略设置加载和准备数据"""
    
    def __init__(self, db: DatabaseManager):
        """
        初始化数据加载器
        
        Args:
            db: 数据库管理器实例
        """
        self.db = db
    
    def load_stock_data(self, stock_id: str, settings: Dict[str, Any], strategy_name: str = "Unknown") -> Dict[str, List[Dict[str, Any]]]:
        """
        根据策略设置加载股票数据
        
        Args:
            stock_id: 股票ID
            settings: 策略设置（应该已经验证过）
            strategy_name: 策略名称
            
        Returns:
            Dict: 包含不同周期K线数据的字典
        """
        kline_config = settings.get('klines', {})
        base_term = kline_config.get('base_term', 'daily')
        
        # 加载基础周期数据
        base_data = self._load_kline_data(stock_id, base_term)
        
        # 加载其他周期数据（如果需要）
        term_data = {base_term: base_data}
        
        # 加载其他配置的周期
        for term in kline_config.get('additional_terms', []):
            term_data[term] = self._load_kline_data(stock_id, term)
        
        return term_data
    
    def _load_kline_data(self, stock_id: str, term: str) -> List[Dict[str, Any]]:
        """
        加载指定周期的K线数据
        
        Args:
            stock_id: 股票ID
            term: 数据周期 (daily, weekly, monthly等)
            
        Returns:
            List[Dict]: K线数据列表
        """
        try:
            kline_table = self.db.get_table_instance('stock_kline')
            return kline_table.get_all_k_lines_by_term(stock_id, term)
        except Exception as e:
            logger.error(f"❌ 加载股票 {stock_id} {term} 数据失败: {e}")
            return []
    
    def load_stock_list(self, settings: Dict[str, Any], strategy_name: str = "Unknown") -> List[Dict[str, Any]]:
        """
        根据策略设置加载股票列表
        
        Args:
            settings: 策略设置（应该已经验证过）
            strategy_name: 策略名称
            
        Returns:
            List[Dict]: 股票列表
        """
        try:
            stock_index_table = self.db.get_table_instance("stock_index")
            return stock_index_table.load_filtered_index()
        except Exception as e:
            logger.error(f"❌ 加载股票列表失败: {e}")
            return []
    
    def prepare_scan_data(self, stock_id: str, settings: Dict[str, Any], strategy_name: str = "Unknown") -> Dict[str, Any]:
        """
        为扫描准备数据
        
        Args:
            stock_id: 股票ID
            settings: 策略设置（应该已经验证过）
            strategy_name: 策略名称
            
        Returns:
            Dict: 准备好的数据
        """
        return {
            'stock_id': stock_id,
            'data': self.load_stock_data(stock_id, settings, strategy_name),
            'settings': settings
        }
    
    def prepare_simulation_data(self, stock_id: str, settings: Dict[str, Any], strategy_name: str = "Unknown") -> Dict[str, Any]:
        """
        为模拟准备数据
        
        Args:
            stock_id: 股票ID
            settings: 策略设置（应该已经验证过）
            strategy_name: 策略名称
            
        Returns:
            Dict: 准备好的数据
        """
        kline_config = settings.get('klines', {})
        base_term = kline_config.get('base_term', 'daily')
        
        # 加载基础周期数据用于模拟
        base_data = self._load_kline_data(stock_id, base_term)
        
        return {
            'stock_id': stock_id,
            'klines': {base_term: base_data},
            'settings': settings
        }
