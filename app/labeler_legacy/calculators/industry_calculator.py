#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
行业分类标签计算器
"""

from typing import Optional
from loguru import logger
from ..base_calculator import BaseLabelCalculator
from ..conf.label_mapping import LabelMapping


class IndustryLabelCalculator(BaseLabelCalculator):
    """行业分类标签计算器"""
    
    def get_label_category(self) -> str:
        """获取标签分类"""
        return 'industry'
    
    def calculate_label(self, stock_id: str, target_date: str, **kwargs) -> Optional[str]:
        """
        计算行业分类标签
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期 (YYYYMMDD格式)
            **kwargs: 其他参数，可能包含：
                - klines_data: 预加载的K线数据列表（行业计算器不使用）
                - data_mgr: 数据管理器（用于获取股票信息）
            
        Returns:
            str: 标签ID (finance/technology/consumer等)
        """
        try:
            # 获取数据管理器
            data_mgr = kwargs.get('data_mgr')
            
            if data_mgr is None:
                logger.warning(f"无法获取 {stock_id} 的数据加载器")
                return None
            
            # 获取股票基本信息
            stock_info = data_mgr.get_stock_info(stock_id)
            
            if not stock_info:
                logger.warning(f"无法获取 {stock_id} 的股票信息")
                return None
            
            industry = stock_info.get('industry', '').strip()
            
            if not industry:
                logger.warning(f"{stock_id} 的行业信息为空")
                return None
            
            # 根据行业匹配标签
            for label_id, label_def in LabelMapping.INDUSTRY_LABELS.items():
                industries = label_def.get('industries', [])
                for industry_keyword in industries:
                    if industry_keyword in industry:
                        return label_id
            
            # 如果没有匹配到，返回默认标签
            logger.info(f"{stock_id} 的行业 {industry} 未匹配到具体分类，使用默认分类")
            return 'manufacturing'  # 默认归类为制造业
            
        except Exception as e:
            logger.error(f"计算行业标签失败 {stock_id} {target_date}: {e}")
            return None
