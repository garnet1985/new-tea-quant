#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
标签器配置文件
定义标签更新频率、计算参数等配置
"""

from enum import Enum
from typing import Dict, Any, List


class UpdateFrequency(Enum):
    """更新频率枚举"""
    DAILY = "daily"           # 每日更新
    WEEKLY = "weekly"         # 每周更新  
    BIWEEKLY = "biweekly"     # 每两周更新
    MONTHLY = "monthly"       # 每月更新
    QUARTERLY = "quarterly"   # 每季度更新
    YEARLY = "yearly"         # 每年更新


class LabelConfig:
    """标签配置管理类"""
    
    # 统一更新周期（天）
    UPDATE_INTERVAL_DAYS = 30  # 1个月更新一次
    
    # 不需要重新计算的标签分类（相对稳定）
    STATIC_CATEGORIES = ['industry']  # 行业标签不需要重新计算
    
    # 计算参数配置
    CALCULATION_CONFIG = {
        # 波动性计算参数
        'volatility': {
            'lookback_days': 30,           # 回看天数
            'min_trading_days': 20         # 最小交易天数
        },
        # 成交量计算参数
        'volume': {
            'lookback_days': 20,           # 回看天数
            'min_trading_days': 15         # 最小交易天数
        },
        # 市值计算参数
        'market_cap': {
            'use_latest_price': True,      # 使用最新价格计算市值
            'fallback_to_book_value': True # 市值缺失时使用账面价值
        },
        # 财务指标计算参数
        'financial': {
            'use_latest_report': True,     # 使用最新财报
            'quarterly_fallback': True     # 季报缺失时使用年报
        }
    }
    
    # 性能配置
    PERFORMANCE_CONFIG = {
        'max_workers': 10,                 # 最大工作线程数
        'batch_size': 100,                 # 批处理大小
        'chunk_size': 50,                  # 分块大小
        'timeout_seconds': 300,            # 超时时间（秒）
        'retry_attempts': 3,               # 重试次数
        'multithread_threshold': 50,       # 多线程阈值（股票数量）
        'max_threads_limit': 20            # 最大线程数限制
    }
    
    # 数据质量配置
    DATA_QUALITY_CONFIG = {
        'min_data_points': 10,             # 最小数据点数
        'max_missing_ratio': 0.3,          # 最大缺失比例
        'outlier_threshold': 3.0,          # 异常值阈值（标准差倍数）
        'validate_calculations': True      # 验证计算结果
    }
    
    @classmethod
    def should_update_stock(cls, days_since_update: int) -> bool:
        """
        判断股票是否需要更新标签
        
        Args:
            days_since_update: 距离上次更新的天数
            
        Returns:
            bool: 是否需要更新
        """
        return days_since_update >= cls.UPDATE_INTERVAL_DAYS
    
    @classmethod
    def is_static_category(cls, category: str) -> bool:
        """
        判断标签分类是否为静态（不需要重新计算）
        
        Args:
            category: 标签分类
            
        Returns:
            bool: 是否为静态分类
        """
        return category in cls.STATIC_CATEGORIES
    
    @classmethod
    def get_update_interval_days(cls) -> int:
        """
        获取更新周期天数
        
        Returns:
            int: 更新周期天数
        """
        return cls.UPDATE_INTERVAL_DAYS
    
    @classmethod
    def get_static_categories(cls) -> List[str]:
        """
        获取静态标签分类列表
        
        Returns:
            List[str]: 静态分类列表
        """
        return cls.STATIC_CATEGORIES.copy()
    
    @classmethod
    def get_performance_config(cls) -> Dict[str, Any]:
        """
        获取性能配置
        
        Returns:
            Dict[str, Any]: 性能配置
        """
        return cls.PERFORMANCE_CONFIG.copy()
    
    @classmethod
    def get_calculation_config(cls, category: str) -> Dict[str, Any]:
        """
        获取指定分类的计算配置
        
        Args:
            category: 标签分类
            
        Returns:
            Dict[str, Any]: 计算配置
        """
        return cls.CALCULATION_CONFIG.get(category, {})
    
    @classmethod
    def get_data_quality_config(cls) -> Dict[str, Any]:
        """
        获取数据质量配置
        
        Returns:
            Dict[str, Any]: 数据质量配置
        """
        return cls.DATA_QUALITY_CONFIG.copy()