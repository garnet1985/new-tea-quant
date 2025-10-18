#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财务指标标签计算器
"""

from typing import Optional
from loguru import logger
from ..base_calculator import BaseLabelCalculator
from ..label_mapping import LabelMapping


class FinancialLabelCalculator(BaseLabelCalculator):
    """财务指标标签计算器"""
    
    def get_label_category(self) -> str:
        """获取标签分类"""
        return 'financial'
    
    def calculate_label(self, stock_id: str, target_date: str, **kwargs) -> Optional[str]:
        """
        计算财务指标标签
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期 (YYYYMMDD格式)
            
        Returns:
            str: 标签ID (high_pe/medium_pe/low_pe等)
        """
        try:
            # 获取股票K线数据
            klines = self.data_loader.load_klines(stock_id, start_date=target_date, end_date=target_date)
            
            if not klines or len(klines) == 0:
                logger.warning(f"无法获取 {stock_id} 在 {target_date} 的K线数据")
                return None
            
            # 获取最新的财务指标数据
            latest_kline = klines[-1]
            pe_ratio = latest_kline.get('pe', 0)
            pb_ratio = latest_kline.get('pb', 0)
            
            # 优先返回PE标签
            if pe_ratio > 0:
                if pe_ratio >= LabelMapping.FINANCIAL_LABELS['high_pe']['threshold']:
                    return 'high_pe'
                elif pe_ratio >= LabelMapping.FINANCIAL_LABELS['medium_pe']['threshold_min']:
                    return 'medium_pe'
                else:
                    return 'low_pe'
            
            # 如果PE无效，使用PB
            elif pb_ratio > 0:
                if pb_ratio >= LabelMapping.FINANCIAL_LABELS['high_pb']['threshold']:
                    return 'high_pb'
                elif pb_ratio >= LabelMapping.FINANCIAL_LABELS['medium_pb']['threshold_min']:
                    return 'medium_pb'
                else:
                    return 'low_pb'
            
            else:
                logger.warning(f"{stock_id} 在 {target_date} 的财务指标数据无效")
                return None
                
        except Exception as e:
            logger.error(f"计算财务标签失败 {stock_id} {target_date}: {e}")
            return None
