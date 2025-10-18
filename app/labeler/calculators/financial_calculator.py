#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
财务指标标签计算器
"""

from typing import Optional, List
from loguru import logger
from ..base_calculator import BaseLabelCalculator
from ..conf.label_mapping import LabelMapping


class FinancialLabelCalculator(BaseLabelCalculator):
    """财务指标标签计算器"""
    
    def get_label_category(self) -> str:
        """获取标签分类"""
        return 'financial'
    
    def calculate_label(self, stock_id: str, target_date: str, **kwargs) -> Optional[str]:
        """
        计算财务指标标签（单标签模式，向后兼容）
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期 (YYYYMMDD格式)
            
        Returns:
            str: 标签ID (high_pe/medium_pe/low_pe等)
        """
        labels = self.calculate_labels(stock_id, target_date, **kwargs)
        return labels[0] if labels else None
    
    def calculate_labels(self, stock_id: str, target_date: str, **kwargs) -> List[str]:
        """
        计算财务指标标签（多标签模式）
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期 (YYYYMMDD格式)
            **kwargs: 其他参数，可能包含：
                - klines_data: 预加载的K线数据列表
                - data_loader: 数据加载器（如果没有预加载数据时使用）
            
        Returns:
            List[str]: 标签ID列表 (可能包含PE和PB标签)
        """
        try:
            # 优先使用预加载的K线数据
            klines_data = kwargs.get('klines_data')
            data_loader = kwargs.get('data_loader')
            
            if klines_data is not None:
                klines = klines_data
            elif data_loader is not None:
                klines = data_loader.load_klines(stock_id, start_date=target_date, end_date=target_date)
                logger.debug(f"在使用data_loader加载K线数据")
            else:
                logger.warning(f"无法获取 {stock_id} 在 {target_date} 的K线数据源")
                return []
            
            if not klines or len(klines) == 0:
                logger.warning(f"无法获取 {stock_id} 在 {target_date} 的K线数据")
                return []
            
            # 获取最新的财务指标数据
            latest_kline = klines[-1]
            pe_ratio = latest_kline.get('pe', 0)
            pb_ratio = latest_kline.get('pb', 0)
            
            labels = []
            
            # 计算PE标签
            if pe_ratio > 0:
                if pe_ratio >= LabelMapping.FINANCIAL_LABELS['high_pe']['threshold']:
                    labels.append('high_pe')
                elif pe_ratio >= LabelMapping.FINANCIAL_LABELS['medium_pe']['threshold_min']:
                    labels.append('medium_pe')
                else:
                    labels.append('low_pe')
            
            # 计算PB标签
            if pb_ratio > 0:
                if pb_ratio >= LabelMapping.FINANCIAL_LABELS['high_pb']['threshold']:
                    labels.append('high_pb')
                elif pb_ratio >= LabelMapping.FINANCIAL_LABELS['medium_pb']['threshold_min']:
                    labels.append('medium_pb')
                else:
                    labels.append('low_pb')
            
            if not labels:
                logger.warning(f"{stock_id} 在 {target_date} 的财务指标数据无效")
            
            return labels
                
        except Exception as e:
            logger.error(f"计算财务标签失败 {stock_id} {target_date}: {e}")
            return []
