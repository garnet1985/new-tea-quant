"""
实体组件 - 提供投资目标管理、投资分析等通用功能
"""

from .opportunity import Opportunity
from .target import InvestmentTarget

__all__ = ['Opportunity', 'InvestmentTarget']
