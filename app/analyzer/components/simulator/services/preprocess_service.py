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
    
    # @staticmethod
    # def validate_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    #     """
    #     验证策略设置
        
    #     Args:
    #         settings: 原始设置
            
    #     Returns:
    #         Dict: 验证后的设置
    #     """
    #     logger.info(f"{IconService.get('search')} 验证策略设置...")
        
    #     # 检查必需的设置
    #     if 'simulation' not in settings:
    #         raise ValueError("缺少 'simulation' 设置")
        
    #     simulation_config = settings['simulation']
        
    #     # 设置默认值
    #     from app.conf.conf import data_default_start_date
    #     start_date = simulation_config.get('start_date', data_default_start_date)  # 使用全局默认日期
    #     end_date = simulation_config.get('end_date', '')  # 空字符串表示到最后
        
    #     # 获取klines配置（从顶层读取）
    #     klines_config = settings.get('klines', {})
    #     base_term = klines_config.get('base_term', 'daily')
        
    #     validated_config = {
    #         'simulate_base_term': base_term,
    #         'start_date': start_date,
    #         'end_date': end_date,
    #     }
        
    #     # 透传顶层关键信息（如策略文件夹名、兼容旧字段）
    #     validated_settings = {
    #         'simulation': validated_config,
    #         'klines': klines_config,
    #         'mode': settings.get('mode', {}),
    #     }
    #     if 'folder_name' in settings:
    #         validated_settings['folder_name'] = settings['folder_name']
    #     if 'strategy_name' in settings:
    #         validated_settings['strategy_name'] = settings['strategy_name']
        
    #     logger.info(f"{IconService.get('success')} 设置验证完成: {validated_config}")
    #     return validated_settings
    
    # @staticmethod
    # def validate_simulate_one_day_func(func: Optional[Callable]) -> bool:
    #     """
    #     验证单日模拟函数的签名
        
    #     Args:
    #         func: 要验证的函数
            
    #     Returns:
    #         bool: 验证是否通过
            
    #     Raises:
    #         ValueError: 函数签名不符合要求
    #     """
    #     if func is None:
    #         logger.warning(f"{IconService.get('warning')} 未提供单日模拟函数，将使用默认实现")
    #         return True
        
    #     logger.info(f"{IconService.get('search')} 验证单日模拟函数签名...")
        
    #     try:
    #         # 获取函数签名
    #         sig = inspect.signature(func)
    #         params = list(sig.parameters.keys())
            
    #         # 检查参数数量 - 绑定方法有5个参数（不包括self），未绑定方法有6个参数（包括self）
    #         expected_params = 5 if hasattr(func, '__self__') else 6
    #         if len(params) != expected_params:
    #             raise ValueError(f"函数参数数量错误: 期望{expected_params}个参数，实际{len(params)}个")
            
    #         # 检查参数名称
    #         if hasattr(func, '__self__'):
    #             # 绑定方法：不包含self参数
    #             expected_params = ['stock_id', 'current_date', 'current_record', 'all_data', 'current_investment', 'settings']
    #         else:
    #             # 未绑定方法：包含self参数
    #             expected_params = ['self', 'stock_id', 'current_date', 'current_record', 'all_data', 'current_investment', 'settings']
            
    #         if params != expected_params:
    #             raise ValueError(f"函数参数名称错误: 期望{expected_params}，实际{params}")
            
    #         # 检查函数是否可调用
    #         if not callable(func):
    #             raise ValueError("提供的对象不是可调用函数")
            
    #         logger.info(f"{IconService.get('success')} 单日模拟函数验证通过: {func.__name__}")
    #         return True
            
    #     except Exception as e:
    #         logger.error(f"{IconService.get('error')} 单日模拟函数验证失败: {e}")
    #         raise ValueError(f"单日模拟函数验证失败: {e}")

    @staticmethod
    def get_stock_list(settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        获取股票列表
        
        Args:
            settings: 策略设置
            
        Returns:
            List[Dict]: 股票列表
        """
        logger.info("📋 获取股票列表...")
        
        # 获取股票列表配置（从顶层mode配置读取）
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
    
    @staticmethod
    def preprocess(settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        完整的预处理流程

        Args:
            settings: 原始设置
            
        Returns:
            list: stock_list
        """
        
        # 获取股票列表
        return PreprocessService.get_stock_list(settings)
