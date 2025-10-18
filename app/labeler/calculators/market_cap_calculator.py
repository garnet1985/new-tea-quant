#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
市值规模标签计算器
"""

from typing import Optional
from loguru import logger
from ..base_calculator import BaseLabelCalculator
from ..label_mapping import LabelMapping


class MarketCapLabelCalculator(BaseLabelCalculator):
    """市值规模标签计算器"""
    
    def get_label_category(self) -> str:
        """获取标签分类"""
        return 'market_cap'
    
    def calculate_label(self, stock_id: str, target_date: str, **kwargs) -> Optional[str]:
        """
        计算市值规模标签
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期 (YYYYMMDD格式)
            
        Returns:
            str: 标签ID (large_cap/mid_cap/small_cap)
        """
        try:
            # 获取股票K线数据
            klines = self.data_loader.load_klines(stock_id, start_date=target_date, end_date=target_date)
            
            if not klines or len(klines) == 0:
                logger.warning(f"无法获取 {stock_id} 在 {target_date} 的K线数据")
                return None
            
            # 获取最新的市值数据
            latest_kline = klines[-1]
            market_cap = latest_kline.get('total_market_value', 0)
            
            if market_cap <= 0:
                logger.warning(f"{stock_id} 在 {target_date} 的市值数据无效: {market_cap}")
                return None
            
            # 根据市值确定标签
            if market_cap >= LabelMapping.MARKET_CAP_LABELS['large_cap']['threshold']:
                return 'large_cap'
            elif market_cap >= LabelMapping.MARKET_CAP_LABELS['mid_cap']['threshold_min']:
                return 'mid_cap'
            else:
                return 'small_cap'
                
        except Exception as e:
            logger.error(f"计算市值标签失败 {stock_id} {target_date}: {e}")
            return None
