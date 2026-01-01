#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
成交量标签计算器
"""

from typing import Optional
from loguru import logger
from ..base_calculator import BaseLabelCalculator
from ..conf.label_mapping import LabelMapping


class VolumeLabelCalculator(BaseLabelCalculator):
    """成交量标签计算器"""
    
    def get_label_category(self) -> str:
        """获取标签分类"""
        return 'volume'
    
    def calculate_label(self, stock_id: str, target_date: str, lookback_days: int = 30, **kwargs) -> Optional[str]:
        """
        计算成交量标签
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期 (YYYYMMDD格式)
            lookback_days: 回望天数，默认30天
            **kwargs: 其他参数，可能包含：
                - klines_data: 预加载的K线数据列表
                - data_mgr: 数据管理器（如果没有预加载数据时使用）
            
        Returns:
            str: 标签ID (high_volume/medium_volume/low_volume)
        """
        try:
            # 计算回望开始日期
            from datetime import datetime, timedelta
            target_datetime = datetime.strptime(target_date, '%Y%m%d')
            start_datetime = target_datetime - timedelta(days=lookback_days)
            start_date = start_datetime.strftime('%Y%m%d')
            
            # 优先使用预加载的K线数据
            klines_data = kwargs.get('klines_data')
            data_mgr = kwargs.get('data_mgr')
            
            if klines_data is not None:
                # 使用预加载数据，但需要筛选出回望期间的数据
                klines = [k for k in klines_data if k.get('date', '') >= start_date and k.get('date', '') <= target_date]
            elif data_mgr is not None:
                klines = data_mgr.load_klines(stock_id, start_date=start_date, end_date=target_date)
            else:
                logger.warning(f"无法获取 {stock_id} 在 {target_date} 的K线数据源")
                return None
            
            if not klines or len(klines) < 10:
                return None
            
            # 计算成交量比率
            volumes = [k['volume'] for k in klines if k['volume'] > 0]
            if len(volumes) < 2:
                logger.warning(f"{stock_id} 的有效成交量数据不足")
                return None
            
            # 计算平均成交量
            avg_volume = sum(volumes) / len(volumes)
            
            # 获取最新成交量
            latest_volume = volumes[-1]
            
            # 计算成交量比率
            volume_ratio = latest_volume / avg_volume if avg_volume > 0 else 0
            
            # 根据成交量比率确定标签
            if volume_ratio >= LabelMapping.VOLUME_LABELS['high_volume']['threshold']:
                return 'high_volume'
            elif volume_ratio >= LabelMapping.VOLUME_LABELS['medium_volume']['threshold_min']:
                return 'medium_volume'
            else:
                return 'low_volume'
                
        except Exception as e:
            logger.error(f"计算成交量标签失败 {stock_id} {target_date}: {e}")
            return None
