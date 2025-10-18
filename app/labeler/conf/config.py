#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
标签系统配置管理
"""

from typing import Dict, Any
from enum import Enum


class UpdateFrequency(Enum):
    """更新频率枚举"""
    DAILY = "daily"           # 每日更新
    WEEKLY = "weekly"         # 每周更新
    MONTHLY = "monthly"       # 每月更新
    QUARTERLY = "quarterly"   # 每季度更新
    YEARLY = "yearly"         # 每年更新
    ON_DEMAND = "on_demand"   # 按需更新


class LabelConfig:
    """标签配置管理器"""
    
    # 标签更新频率配置
    LABEL_UPDATE_FREQUENCY = {
        # 市值规模 - 每日更新（市值变化频繁）
        'market_cap': UpdateFrequency.DAILY,
        
        # 行业分类 - 季度更新（行业分类相对稳定）
        'industry': UpdateFrequency.QUARTERLY,
        
        # 波动性 - 每周更新（波动性需要一定时间窗口）
        'volatility': UpdateFrequency.WEEKLY,
        
        # 成交量 - 每日更新（成交量变化频繁）
        'volume': UpdateFrequency.DAILY,
        
        # 财务指标 - 季度更新（财务数据按季度发布）
        'financial': UpdateFrequency.QUARTERLY,
        
        # 技术指标 - 每日更新（技术指标实时计算）
        'technical': UpdateFrequency.DAILY,
        
        # 成长性 - 季度更新（成长性基于财务数据）
        'growth': UpdateFrequency.QUARTERLY,
        
        # 价值指标 - 季度更新（价值指标基于财务数据）
        'value': UpdateFrequency.QUARTERLY,
    }
    
    # 标签计算参数配置
    LABEL_CALCULATION_PARAMS = {
        'volatility': {
            'lookback_days': 30,  # 波动性计算回望天数
            'min_data_points': 10,  # 最少数据点数
        },
        'volume': {
            'lookback_days': 30,  # 成交量比率计算回望天数
            'min_data_points': 10,  # 最少数据点数
        },
        'financial': {
            'pe_threshold_high': 50,  # 高PE阈值
            'pe_threshold_low': 15,   # 低PE阈值
            'pb_threshold_high': 5,   # 高PB阈值
            'pb_threshold_low': 1,    # 低PB阈值
        },
        'market_cap': {
            'large_cap_threshold': 10000000000,  # 大盘股阈值（100亿）
            'mid_cap_threshold_min': 3000000000,  # 中盘股最小阈值（30亿）
            'mid_cap_threshold_max': 10000000000,  # 中盘股最大阈值（100亿）
        }
    }
    
    # 标签优先级配置（数字越小优先级越高）
    LABEL_PRIORITY = {
        'market_cap': 1,      # 市值规模 - 最高优先级
        'industry': 2,        # 行业分类
        'financial': 3,       # 财务指标
        'volatility': 4,      # 波动性
        'volume': 5,          # 成交量
        'technical': 6,       # 技术指标
        'growth': 7,          # 成长性
        'value': 8,           # 价值指标
    }
    
    # 标签依赖关系配置
    LABEL_DEPENDENCIES = {
        'volatility': ['market_cap'],  # 波动性计算依赖市值数据
        'volume': ['market_cap'],      # 成交量计算依赖市值数据
        'technical': ['market_cap'],   # 技术指标计算依赖市值数据
        'financial': ['market_cap'],   # 财务指标计算依赖市值数据
    }
    
    # 标签计算超时配置（秒）
    LABEL_TIMEOUT = {
        'market_cap': 30,     # 市值计算超时
        'industry': 10,       # 行业分类超时
        'volatility': 60,     # 波动性计算超时
        'volume': 60,         # 成交量计算超时
        'financial': 30,      # 财务指标超时
        'technical': 120,     # 技术指标超时
        'growth': 60,         # 成长性计算超时
        'value': 60,          # 价值指标超时
    }
    
    @classmethod
    def get_update_frequency(cls, label_category: str) -> UpdateFrequency:
        """
        获取标签分类的更新频率
        
        Args:
            label_category: 标签分类
            
        Returns:
            UpdateFrequency: 更新频率
        """
        return cls.LABEL_UPDATE_FREQUENCY.get(label_category, UpdateFrequency.MONTHLY)
    
    @classmethod
    def get_calculation_params(cls, label_category: str) -> Dict[str, Any]:
        """
        获取标签分类的计算参数
        
        Args:
            label_category: 标签分类
            
        Returns:
            Dict[str, Any]: 计算参数
        """
        return cls.LABEL_CALCULATION_PARAMS.get(label_category, {})
    
    @classmethod
    def get_priority(cls, label_category: str) -> int:
        """
        获取标签分类的优先级
        
        Args:
            label_category: 标签分类
            
        Returns:
            int: 优先级（数字越小优先级越高）
        """
        return cls.LABEL_PRIORITY.get(label_category, 999)
    
    @classmethod
    def get_dependencies(cls, label_category: str) -> list:
        """
        获取标签分类的依赖关系
        
        Args:
            label_category: 标签分类
            
        Returns:
            list: 依赖的标签分类列表
        """
        return cls.LABEL_DEPENDENCIES.get(label_category, [])
    
    @classmethod
    def get_timeout(cls, label_category: str) -> int:
        """
        获取标签分类的计算超时时间
        
        Args:
            label_category: 标签分类
            
        Returns:
            int: 超时时间（秒）
        """
        return cls.LABEL_TIMEOUT.get(label_category, 60)
    
    @classmethod
    def get_sorted_categories_by_priority(cls) -> list:
        """
        按优先级排序的标签分类列表
        
        Returns:
            list: 按优先级排序的标签分类列表
        """
        return sorted(cls.LABEL_PRIORITY.keys(), key=lambda x: cls.LABEL_PRIORITY[x])
    
    @classmethod
    def get_categories_by_frequency(cls, frequency: UpdateFrequency) -> list:
        """
        根据更新频率获取标签分类列表
        
        Args:
            frequency: 更新频率
            
        Returns:
            list: 该频率下的标签分类列表
        """
        return [category for category, freq in cls.LABEL_UPDATE_FREQUENCY.items() 
                if freq == frequency]
    
    @classmethod
    def get_config_summary(cls) -> Dict[str, Any]:
        """
        获取配置摘要信息
        
        Returns:
            Dict[str, Any]: 配置摘要
        """
        return {
            'total_categories': len(cls.LABEL_UPDATE_FREQUENCY),
            'update_frequencies': {category: freq.value for category, freq in cls.LABEL_UPDATE_FREQUENCY.items()},
            'priorities': cls.LABEL_PRIORITY.copy(),
            'dependencies': cls.LABEL_DEPENDENCIES.copy(),
            'timeouts': cls.LABEL_TIMEOUT.copy(),
            'calculation_params': {k: len(v) for k, v in cls.LABEL_CALCULATION_PARAMS.items()}
        }
