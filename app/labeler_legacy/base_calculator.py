#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Labeler基类定义
提供通用的标签计算接口和可扩展的架构
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date
import pandas as pd
from loguru import logger


class BaseLabelCalculator(ABC):
    """标签计算器基类"""
    
    def __init__(self, data_mgr):
        """
        初始化标签计算器
        
        Args:
            data_mgr: 数据管理器实例
        """
        self.data_mgr = data_mgr
        self.label_category = self.get_label_category()
        self.calculated_labels = {}  # 缓存计算结果
    
    @abstractmethod
    def get_label_category(self) -> str:
        """
        获取标签分类
        
        Returns:
            str: 标签分类名称
        """
        pass

    @abstractmethod
    def calculate_label(self, stock_id: str, target_date: str, **kwargs) -> Optional[str]:
        """
        计算单个标签
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期 (YYYYMMDD格式)
            **kwargs: 其他参数
            
        Returns:
            str: 标签ID，如果无法计算返回None
        """
        pass
    
    def calculate_labels_for_stock(self, stock_id: str, target_date: str, **kwargs) -> List[str]:
        """
        为单个股票计算所有相关标签
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期 (YYYYMMDD格式)
            **kwargs: 其他参数，可能包含：
                - klines_data: 预加载的K线数据列表
                - data_mgr: 数据管理器（如果没有预加载数据时使用）
            
        Returns:
            List[str]: 标签ID列表
        """
        try:
            # 检查是否有预加载的K线数据
            klines_data = kwargs.get('klines_data')
            data_mgr = kwargs.get('data_mgr')
            
            if klines_data is not None:
                # 使用预加载的数据
                kwargs_with_klines = {**kwargs, 'klines_data': klines_data}
            elif data_mgr is not None:
                # 回退到动态加载数据
                kwargs_with_klines = {**kwargs, 'data_mgr': data_mgr}
            else:
                # 没有数据源，返回空列表
                logger.warning(f"计算标签 {stock_id} {target_date} 没有可用的数据源")
                return []
            
            # 优先使用多标签计算方法
            if hasattr(self, 'calculate_labels') and callable(getattr(self, 'calculate_labels')):
                return self.calculate_labels(stock_id, target_date, **kwargs_with_klines)
            else:
                # 回退到单标签计算方法
                label_id = self.calculate_label(stock_id, target_date, **kwargs_with_klines)
                return [label_id] if label_id else []
        except Exception as e:
            logger.error(f"计算标签失败 {stock_id} {target_date}: {e}")
            return []
    
    def calculate_labels(self, stock_id: str, target_date: str, **kwargs) -> List[str]:
        """
        计算多个标签（子类可选实现）
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期 (YYYYMMDD格式)
            **kwargs: 其他参数
            
        Returns:
            List[str]: 标签ID列表，如果无法计算返回空列表
        """
        # 默认实现：调用单个标签计算方法
        label = self.calculate_label(stock_id, target_date, **kwargs)
        return [label] if label else []
    
    def batch_calculate_labels(self, stock_ids: List[str], target_date: str, **kwargs) -> Dict[str, List[str]]:
        """
        批量计算标签
        
        Args:
            stock_ids: 股票代码列表
            target_date: 目标日期 (YYYYMMDD格式)
            **kwargs: 其他参数
            
        Returns:
            Dict[str, List[str]]: 股票代码到标签列表的映射
        """
        results = {}
        
        for stock_id in stock_ids:
            labels = self.calculate_labels_for_stock(stock_id, target_date, **kwargs)
            if labels:
                results[stock_id] = labels
        
        return results
    
    def get_available_labels(self) -> List[Dict[str, Any]]:
        """
        获取当前分类下所有可用的标签定义
        
        Returns:
            List[Dict[str, Any]]: 标签定义列表
        """
        from .conf.label_mapping import LabelMapping
        return list(LabelMapping.get_labels_by_category(self.label_category).values())
    
    def validate_label_data(self, stock_id: str, target_date: str, required_data: List[str]) -> bool:
        """
        验证标签计算所需的数据是否可用
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期
            required_data: 需要的数据字段列表
            
        Returns:
            bool: 数据是否可用
        """
        try:
            # 这里可以添加数据可用性检查逻辑
            # 例如检查K线数据是否存在、财务数据是否可用等
            return True
        except Exception as e:
            logger.warning(f"数据验证失败 {stock_id} {target_date}: {e}")
            return False
    
    def get_cache_key(self, stock_id: str, target_date: str) -> str:
        """
        生成缓存键
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期
            
        Returns:
            str: 缓存键
        """
        return f"{self.label_category}:{stock_id}:{target_date}"
    
    def clear_cache(self):
        """清空缓存"""
        self.calculated_labels.clear()
        logger.info(f"已清空 {self.label_category} 标签计算器缓存")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            Dict[str, Any]: 缓存统计信息
        """
        return {
            'category': self.label_category,
            'cached_items': len(self.calculated_labels),
            'cache_keys': list(self.calculated_labels.keys())
        }


class LabelCalculatorRegistry:
    """标签计算器注册表"""
    
    def __init__(self):
        self.calculators = {}
        self.categories = {}
    
    def register_calculator(self, calculator_class: type, category: str):
        """
        注册标签计算器
        
        Args:
            calculator_class: 计算器类
            category: 标签分类
        """
        self.calculators[category] = calculator_class
        self.categories[category] = category
    
    def get_calculator(self, category: str, data_mgr, label_definitions):
        """
        获取标签计算器实例
        
        Args:
            category: 标签分类
            data_mgr: 数据管理器
            label_definitions: 标签定义管理器
            
        Returns:
            BaseLabelCalculator: 计算器实例
        """
        if category not in self.calculators:
            raise ValueError(f"未注册的标签计算器分类: {category}")
        
        calculator_class = self.calculators[category]
        return calculator_class(data_mgr)
    
    def get_all_categories(self) -> List[str]:
        """
        获取所有已注册的分类
        
        Returns:
            List[str]: 分类列表
        """
        return list(self.categories.keys())
    
    def get_calculator_info(self) -> Dict[str, str]:
        """
        获取所有计算器的信息
        
        Returns:
            Dict[str, str]: 分类到类名的映射
        """
        return {category: cls.__name__ for category, cls in self.calculators.items()}
