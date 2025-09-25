#!/usr/bin/env python3
"""
PreprocessService - 预处理服务
"""
from typing import Dict, List, Any
from loguru import logger
from utils.icon.icon_service import IconService


class PreprocessService:
    """预处理服务 - 验证设置，获取股票列表"""
    
    @staticmethod
    def get_stock_list(settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        获取股票列表
        
        Args:
            settings: 策略设置
            
        Returns:
            List[Dict]: 股票列表
        """
        
        mode_config = settings.get('mode', {})
        max_stocks = mode_config.get('test_amount', 10)
        start_idx = mode_config.get('start_idx', 0)
        
        try:
            # 从数据库获取股票列表
            from utils.db.db_manager import DatabaseManager
            
            # 创建数据库连接
            db = DatabaseManager()
            db.initialize()
            
            # 获取股票指数表实例
            stock_index_table = db.get_table_instance('stock_index')
            
            # 使用 load_filtered_index 获取过滤后的股票列表
            stock_list = stock_index_table.load_filtered_index()
            
            if max_stocks > 0:
                stock_list = stock_list[start_idx:start_idx + max_stocks]
            
            return stock_list
            
        except Exception as e:
            logger.error(f"{IconService.get('error')} 获取股票列表失败: {e}")
            return []