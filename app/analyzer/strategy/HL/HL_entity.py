#!/usr/bin/env python3
"""
策略实体生成器 - 集中管理所有entity的生成函数
"""
from typing import Dict, Any

from .settings import settings


class HistoricLowEntity:
    """策略实体生成器 - 集中管理所有entity的生成函数"""
    
    @staticmethod
    def to_low_point(term: int, low_point_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成统一格式的历史低点对象：在 low point record 的基础上，计算出投资范围

        Args:
            term: 历史低点年份
            low_point_record: 历史低点记录

        Returns:
            Dict[str, Any]: 统一格式的历史低点对象
        """

        low_point_config = settings.get('low_point_invest_range')

        if not low_point_config:
            raise Exception("low_point_invest_range is not set in strategy_settings.")

        upper_bound_ratio = low_point_config.get('upper_bound')
        lower_bound_ratio = low_point_config.get('lower_bound')
        min_price_gap = low_point_config.get('min')
        max_price_gap = low_point_config.get('max')

        # 计算绝对价格区间
        upper_absolute_range = low_point_record['close'] * upper_bound_ratio
        lower_absolute_range = low_point_record['close'] * lower_bound_ratio

        # 应用最小/最大限制
        if lower_absolute_range < min_price_gap:
            lower_absolute_range = min_price_gap

        if upper_absolute_range > max_price_gap:
            upper_absolute_range = max_price_gap
        
        # 计算最终的投资范围价格
        upper_bound_price = low_point_record['close'] + upper_absolute_range
        lower_bound_price = low_point_record['close'] - lower_absolute_range

        return {
            'term': term,
            'low_point_price': low_point_record.get('close'),
            'date': low_point_record.get('date'),
            'invest_upper_bound': upper_bound_price,
            'invest_lower_bound': lower_bound_price
        }