#!/usr/bin/env python3
"""
股票标签算法服务

位置：app/labeler/（与analyzer、data_loader、data_source并列）

职责：
- 股票标签的计算算法
- 标签分类和定义管理
- 批量标签计算和更新
- 标签质量评估和优化

架构：
- LabelerService: 主服务入口
- BaseLabelCalculator: 标签计算器基类
- 具体计算器: 各种标签的具体计算实现
- LabelMapping: 标签映射定义
- LabelDefinitions: 标签定义管理
- LabelEvaluator: 标签质量评估
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date, timedelta
import pandas as pd
from loguru import logger
from .base_calculator import BaseLabelCalculator, LabelCalculatorRegistry
from .calculators import (
    MarketCapLabelCalculator, 
    IndustryLabelCalculator, 
    VolatilityLabelCalculator,
    VolumeLabelCalculator,
    FinancialLabelCalculator
)
from .label_mapping import LabelMapping
from .definitions import LabelDefinitions
from .evaluator import LabelEvaluator
from utils.db.db_manager import DatabaseManager
from app.data_loader import DataLoader


class LabelerService:
    """
    股票标签服务（主入口）
    
    职责：
    - 提供统一的标签计算API
    - 管理标签计算任务
    - 协调各个标签计算器
    - 提供标签映射查询接口
    """
    
    def __init__(self, db: DatabaseManager = None):
        """
        初始化标签服务
        
        Args:
            db: 数据库管理器实例
        """
        if db is None:
            db = DatabaseManager()
            db.initialize()
        
        self.db = db
        self.data_loader = DataLoader(db)
        self.label_definitions = LabelDefinitions(db)
        self.label_evaluator = LabelEvaluator(self.db)
        
        # 初始化计算器注册表
        self.registry = LabelCalculatorRegistry()
        self._register_calculators()
        
        # 缓存计算器实例
        self._calculator_instances = {}
    
    def _register_calculators(self):
        """注册所有标签计算器"""
        # 注册各种标签计算器
        self.registry.register_calculator(MarketCapLabelCalculator, 'market_cap')
        self.registry.register_calculator(IndustryLabelCalculator, 'industry')
        self.registry.register_calculator(VolatilityLabelCalculator, 'volatility')
        self.registry.register_calculator(VolumeLabelCalculator, 'volume')
        self.registry.register_calculator(FinancialLabelCalculator, 'financial')
        
        logger.info(f"已注册 {len(self.registry.get_all_categories())} 个标签计算器")
    
    def get_calculator(self, category: str) -> BaseLabelCalculator:
        """
        获取标签计算器实例
        
        Args:
            category: 标签分类
            
        Returns:
            BaseLabelCalculator: 计算器实例
        """
        if category not in self._calculator_instances:
            self._calculator_instances[category] = self.registry.get_calculator(
                category, self.data_loader, self.label_definitions
            )
        return self._calculator_instances[category]
    
    def calculate_stock_labels(self, stock_id: str, target_date: str, categories: Optional[List[str]] = None) -> List[str]:
        """
        计算单只股票的标签
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期 (YYYYMMDD格式)
            categories: 要计算的标签分类，None表示计算所有分类
            
        Returns:
            List[str]: 标签ID列表
        """
        all_labels = []
        
        # 确定要计算的分类
        if categories is None:
            categories = self.registry.get_all_categories()
        
        for category in categories:
            try:
                calculator = self.get_calculator(category)
                labels = calculator.calculate_labels_for_stock(stock_id, target_date)
                all_labels.extend(labels)
            except Exception as e:
                logger.error(f"计算 {category} 标签失败 {stock_id}: {e}")
        
        return all_labels
    
    def batch_calculate_labels(self, stock_ids: List[str], target_date: str, categories: Optional[List[str]] = None):
        """
        批量计算股票标签
        
        Args:
            stock_ids: 股票代码列表
            target_date: 目标日期 (YYYYMMDD格式)
            categories: 要计算的标签分类
        """
        logger.info(f"开始批量计算标签: {len(stock_ids)}只股票, 日期: {target_date}")
        
        def calculator_func(stock_id: str, label_date: str) -> List[str]:
            return self.calculate_stock_labels(stock_id, label_date, categories)
        
        self.data_loader.batch_calculate_labels(stock_ids, target_date, calculator_func)
    
    def update_monthly_labels(self, target_date: Optional[str] = None):
        """
        更新月度标签
        
        Args:
            target_date: 目标日期 (YYYYMMDD格式)，None表示当前月份
        """
        if target_date is None:
            target_date = datetime.now().replace(day=1).strftime('%Y%m%d')
        
        logger.info(f"开始更新月度标签: {target_date}")
        
        # 获取所有股票
        stock_list_table = self.db.get_table_instance('stock_list')
        stocks = stock_list_table.load_filtered_stock_list()
        stock_ids = [stock['id'] for stock in stocks]
        
        # 批量计算标签
        self.batch_calculate_labels(stock_ids, target_date)
        
        logger.info(f"月度标签更新完成: {target_date}")
    
    def get_label_statistics(self, target_date: Optional[str] = None) -> Dict[str, Any]:
        """
        获取标签统计信息
        
        Args:
            target_date: 目标日期 (YYYYMMDD格式)
            
        Returns:
            Dict: 标签统计信息
        """
        return self.data_loader.label_loader.get_label_statistics(target_date)
    
    def evaluate_label_quality(self, target_date: Optional[str] = None) -> Dict[str, Any]:
        """
        评估标签质量
        
        Args:
            target_date: 目标日期 (YYYYMMDD格式)
            
        Returns:
            Dict: 标签质量评估结果
        """
        return self.label_evaluator.evaluate_quality(target_date)
    
    # ============ 标签映射查询接口 ============
    
    def get_all_labels(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有标签定义
        
        Returns:
            Dict[str, Dict[str, Any]]: 所有标签定义
        """
        return LabelMapping.get_all_labels()
    
    def get_labels_by_category(self, category: str) -> Dict[str, Dict[str, Any]]:
        """
        根据分类获取标签
        
        Args:
            category: 标签分类
            
        Returns:
            Dict[str, Dict[str, Any]]: 该分类下的标签定义
        """
        return LabelMapping.get_labels_by_category(category)
    
    def get_label_by_id(self, label_id: str) -> Optional[Dict[str, Any]]:
        """
        根据ID获取标签定义
        
        Args:
            label_id: 标签ID
            
        Returns:
            Dict[str, Any]: 标签定义
        """
        return LabelMapping.get_label_by_id(label_id)
    
    def get_categories(self) -> Dict[str, str]:
        """
        获取所有分类定义
        
        Returns:
            Dict[str, str]: 分类ID到名称的映射
        """
        return LabelMapping.get_categories()
    
    def get_label_mapping_info(self) -> Dict[str, Any]:
        """
        获取标签映射的统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return LabelMapping.get_label_mapping_info()
    
    def get_calculator_info(self) -> Dict[str, str]:
        """
        获取所有计算器的信息
        
        Returns:
            Dict[str, str]: 分类到类名的映射
        """
        return self.registry.get_calculator_info()
    
    def get_available_categories(self) -> List[str]:
        """
        获取所有可用的标签分类
        
        Returns:
            List[str]: 分类列表
        """
        return self.registry.get_all_categories()
    
    def validate_label_id(self, label_id: str) -> bool:
        """
        验证标签ID是否有效
        
        Args:
            label_id: 标签ID
            
        Returns:
            bool: 是否有效
        """
        return LabelMapping.validate_label_id(label_id)
    
    def clear_all_caches(self):
        """清空所有计算器缓存"""
        for calculator in self._calculator_instances.values():
            calculator.clear_cache()
        logger.info("已清空所有标签计算器缓存")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取所有计算器的缓存统计
        
        Returns:
            Dict[str, Any]: 缓存统计信息
        """
        stats = {}
        for category, calculator in self._calculator_instances.items():
            stats[category] = calculator.get_cache_stats()
        return stats