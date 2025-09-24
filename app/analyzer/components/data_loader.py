#!/usr/bin/env python3
"""
数据加载器组件 - 根据策略设置加载和准备数据
"""
from typing import Dict, List, Any, Optional
from loguru import logger
from utils.db.db_manager import DatabaseManager


class DataLoader:
    """数据加载器 - 根据策略设置加载和准备数据"""
    
    def __init__(self, db: DatabaseManager = None):
        """
        初始化数据加载器
        
        Args:
            db: 数据库管理器实例
        """
        self.db = db
    
    def load_stock_data(self, stock_id: str, settings: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        根据策略设置加载股票数据
        
        Args:
            stock_id: 股票ID
            settings: 策略设置（应该已经验证过）
            
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

    @staticmethod
    def load_stock_data_in_child_process(stock_id: str, settings: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        子进程安全：在子进程内创建独立 DatabaseManager(use_connection_pool=False)，
        通过表 model API 加载所需周期数据，返回 { term: List[Dict] }。
        """

        kline_config = settings.get('klines', {}) if isinstance(settings, dict) else {}

        try:
            from utils.db.db_manager import DatabaseManager
            db = DatabaseManager()
            db.initialize()
            kline_table = db.get_table_instance('stock_kline')
            adj_factor_table = db.get_table_instance('adj_factor')

            from app.data_source.data_source_service import DataSourceService
            data: Dict[str, List[Dict[str, Any]]] = {}
            
            # 加载基础周期
            for term in kline_config.get('terms', []):
                records = kline_table.get_all_k_lines_by_term(stock_id, term)
                qfq_factors = adj_factor_table.get_stock_factors(stock_id)
                DataSourceService.to_qfq(records, qfq_factors)
                data[term] = DataSourceService.filter_out_negative_records(records)

            return data
        except Exception as e:
            logger.error(f"❌ 加载股票 {stock_id} 数据失败: {e}")
            return {}


    
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