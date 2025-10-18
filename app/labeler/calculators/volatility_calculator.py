#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
波动性标签计算器
"""

from typing import Optional
from loguru import logger
from ..base_calculator import BaseLabelCalculator
from ..conf.label_mapping import LabelMapping


class VolatilityLabelCalculator(BaseLabelCalculator):
    """波动性标签计算器"""
    
    def get_label_category(self) -> str:
        """获取标签分类"""
        return 'volatility'
    
    def calculate_label(self, stock_id: str, target_date: str, lookback_days: int = 30, **kwargs) -> Optional[str]:
        """
        计算波动性标签
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期 (YYYYMMDD格式)
            lookback_days: 回望天数，默认30天
            **kwargs: 其他参数，可能包含：
                - klines_data: 预加载的K线数据列表
                - data_loader: 数据加载器（如果没有预加载数据时使用）
            
        Returns:
            str: 标签ID (high_volatility/medium_volatility/low_volatility)
        """
        try:
            # 计算回望开始日期
            from datetime import datetime, timedelta
            target_datetime = datetime.strptime(target_date, '%Y%m%d')
            start_datetime = target_datetime - timedelta(days=lookback_days)
            start_date = start_datetime.strftime('%Y%m%d')
            
            # 优先使用预加载的K线数据
            klines_data = kwargs.get('klines_data')
            data_loader = kwargs.get('data_loader')
            
            if klines_data is not None:
                # 使用预加载数据，但需要筛选出回望期间的数据
                klines = [k for k in klines_data if k.get('date', '') >= start_date and k.get('date', '') <= target_date]
            elif data_loader is not None:
                klines = data_loader.load_klines(stock_id, start_date=start_date, end_date=target_date)
            else:
                logger.warning(f"无法获取 {stock_id} 在 {target_date} 的K线数据源")
                return None
            
            if not klines or len(klines) < 10:  # 至少需要10天数据
                logger.warning(f"无法获取 {stock_id} 足够的历史数据来计算波动性")
                return None
            
            # 计算收益率
            closes = [k['close'] for k in klines if k['close'] > 0]
            if len(closes) < 2:
                logger.warning(f"{stock_id} 的有效价格数据不足")
                return None
            
            # 计算日收益率
            returns = []
            for i in range(1, len(closes)):
                if closes[i-1] > 0:
                    daily_return = (closes[i] - closes[i-1]) / closes[i-1]
                    returns.append(daily_return)
            
            if len(returns) < 5:  # 至少需要5个收益率数据点
                logger.warning(f"{stock_id} 的收益率数据点不足")
                return None
            
            # 计算波动率（年化）
            import numpy as np
            volatility = np.std(returns) * np.sqrt(252)  # 年化波动率
            
            # 根据波动率确定标签
            if volatility >= LabelMapping.VOLATILITY_LABELS['high_volatility']['threshold']:
                return 'high_volatility'
            elif volatility >= LabelMapping.VOLATILITY_LABELS['medium_volatility']['threshold_min']:
                return 'medium_volatility'
            else:
                return 'low_volatility'
                
        except Exception as e:
            logger.error(f"计算波动性标签失败 {stock_id} {target_date}: {e}")
            return None
