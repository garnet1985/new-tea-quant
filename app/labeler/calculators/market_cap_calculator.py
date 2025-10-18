#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
市值规模标签计算器
"""

from typing import Optional
from loguru import logger
from ..base_calculator import BaseLabelCalculator
from ..conf.label_mapping import LabelMapping


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
            **kwargs: 其他参数，可能包含：
                - klines_data: 预加载的K线数据列表
                - data_loader: 数据加载器（如果没有预加载数据时使用）
            
        Returns:
            str: 标签ID (large_cap/mid_cap/small_cap)
        """
        try:
            # 优先使用预加载的K线数据
            klines_data = kwargs.get('klines_data')
            data_loader = kwargs.get('data_loader')
            
            if klines_data is not None:
                klines = klines_data
            elif data_loader is not None:
                klines = data_loader.load_klines(stock_id, start_date=target_date, end_date=target_date)
            else:
                logger.warning(f"无法获取 {stock_id} 在 {target_date} 的K线数据源")
                return None
            
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
