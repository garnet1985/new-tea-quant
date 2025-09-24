#!/usr/bin/env python3
"""
PreprocessService - 预处理服务
"""
import inspect
from typing import Dict, List, Any, Tuple, Callable, Optional
from loguru import logger
from app.analyzer.components.settings_validator import SettingsValidator
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
            
            # 应用起始索引和数量限制
            end_idx = start_idx + max_stocks
            stock_list = stock_list[start_idx:end_idx]
            
            return stock_list
            
        except Exception as e:
            logger.error(f"{IconService.get('error')} 获取股票列表失败: {e}")
            return []
    
    # @staticmethod
    # def get_module_info(module_static_func: Dict[str, Any]) -> Dict[str, Any]:
    #     """
    #     获取模块信息
    #     """
    #             # 未绑定方法：从函数中获取类信息
    #     qualname = getattr(module_static_func, '__qualname__', '')
    #     strategy_class_name = qualname.split('.')[0] if '.' in qualname else qualname
    #     # 从函数对象中获取模块信息
    #     strategy_module_path = getattr(module_static_func, '__module__', '')

    #     return {
    #         'strategy_class_name': strategy_class_name,
    #         'strategy_module_path': strategy_module_path
    #     }