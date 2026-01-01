#!/usr/bin/env python3
"""
股票标签算法服务模块

位置：app/labeler/（与analyzer、data_manager、data_source并列）

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
"""

# 导出主要类和函数
from .labeler import LabelerService
from .base_calculator import BaseLabelCalculator, LabelCalculatorRegistry
from .conf.config import LabelConfig
from .conf.label_mapping import LabelMapping
from .calculators import (
    MarketCapLabelCalculator,
    IndustryLabelCalculator,
    VolatilityLabelCalculator,
    VolumeLabelCalculator,
    FinancialLabelCalculator
)

# 模块级别的导出
__all__ = [
    'LabelerService',
    'BaseLabelCalculator', 
    'LabelCalculatorRegistry',
    'LabelConfig',
    'LabelMapping',
    'MarketCapLabelCalculator',
    'IndustryLabelCalculator',
    'VolatilityLabelCalculator',
    'VolumeLabelCalculator',
    'FinancialLabelCalculator'
]