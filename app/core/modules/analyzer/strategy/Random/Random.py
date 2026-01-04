#!/usr/bin/env python3
"""
Random策略实现
核心思想：随机掷骰子，5%的概率投资
止盈永远是止损的1.5倍，止损来源于投资前20天的累积振幅delta
"""

import random
import numpy as np
from typing import Any, Dict, List, Optional, Tuple
from loguru import logger

from app.core.modules.analyzer.components.base_strategy import BaseStrategy
from app.enums import KlineTerm
from app.core.modules.analyzer.components.entity.opportunity import Opportunity


class RandomStrategy(BaseStrategy):
    """
    Random策略：随机投资策略
    
    策略特点：
    1. 5%的概率随机投资
    2. 止损基于投资前20天的累积振幅delta
    3. 止盈永远是止损的1.5倍
    """
    
    def __init__(self, is_verbose=False, name="Random", description="Random策略：随机投资策略", key="Random"):
        # 先设置version，再调用父类__init__
        self.version = "1.0.0"
        super().__init__(is_verbose, name, description, key, self.version)
        self.strategy_name = "Lucky investment strategy"
        super().initialize()

    @staticmethod
    def scan_opportunity(stock_info: Dict[str, Any], data: Dict[str, Any], settings: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        扫描投资机会
        
        Args:
            stock_info: 股票信息字典
            data: 股票的历史K线数据（到当前日期为止）
            settings: 策略设置
            
        Returns:
            Optional[Dict]: 如果发现投资机会则返回机会字典，否则返回None
        """
        try:
            stock_id = stock_info.get('id')
            
            # 获取日线数据
            daily_klines = data.get("klines", {}).get("daily", [])
            if not daily_klines or len(daily_klines) < settings['core']['lookback_days'] + 1:
                return None
            
            record_of_today = daily_klines[-1]
            
            # 随机掷骰子决定是否投资
            if RandomStrategy._is_lucky(settings['core']['investment_probability']):
                # 计算投资前20天的累积振幅delta
                # amplitude_delta = RandomStrategy._calculate_amplitude_delta(daily_klines, settings['core']['lookback_days'])

                # if amplitude_delta is None:
                #     return None

                # 计算止损和止盈比例
                # stop_loss_ratio = RandomStrategy._get_stop_loss_ratio(record_of_today, amplitude_delta)
                # take_profit_ratio = RandomStrategy._get_take_profit_ratio(stop_loss_ratio, settings)

                # 创建简化的股票信息（只保留必要字段）
                # simple_stock_info = {
                #     'id': stock_id,
                #     'name': stock_info.get('name', stock_id)
                # }

                return Opportunity(
                    stock=stock_info,
                    record_of_today=record_of_today,
                )

            return None
            
        except Exception as e:
            logger.error(f"❌ Random策略扫描机会失败: {stock_id}, 错误: {e}")
            return None

    @staticmethod
    def _is_lucky(possibility: float) -> bool:
        """
        概率在N%时
        """
        if possibility < 0 or possibility > 1:
            raise ValueError(f"概率范围错误: {possibility}, 范围应为0-1")
        return random.random() <= possibility


    @staticmethod
    def _calculate_amplitude_delta(klines: List[Dict], lookback_days: int) -> Optional[float]:
        """
        计算投资前N天的累积振幅delta
        
        Args:
            klines: K线数据列表
            lookback_days: 回望天数
            
        Returns:
            float: 累积振幅delta，如果计算失败返回None
        """
        try:
            if len(klines) < lookback_days + 1:
                return None
            
            # 获取最近N天的数据
            recent_klines = klines[-lookback_days-1:-1]  # 排除最后一天
            
            if not recent_klines:
                return None
            
            # 计算每天的振幅 (最高价 - 最低价) / 收盘价
            daily_amplitudes = []
            for kline in recent_klines:
                # 兼容不同的字段名
                high = kline.get('highest')
                low = kline.get('lowest')
                close = kline.get('close')
                
                if high is None or low is None or close is None or close <= 0:
                    continue
                    
                amplitude = (high - low) / close
                daily_amplitudes.append(amplitude)
            
            if not daily_amplitudes:
                return None
            
            # 计算累积振幅delta（标准差）
            amplitude_delta = np.std(daily_amplitudes)
            
            return amplitude_delta
            
        except Exception as e:
            logger.error(f"❌ 计算振幅delta失败: {e}")
            return None

    @staticmethod
    def _get_stop_loss_ratio(record_of_today: Dict, amplitude_delta: float) -> float:
        """
        获取止损比例
        
        Args:
            record_of_today: 当日K线数据
            amplitude_delta: 振幅delta
            
        Returns:
            float: 止损比例
        """
        try:
            # 止损比例基于振幅delta，最小-5%，最大-20%
            stop_loss_ratio = max(-0.20, min(-0.05, -amplitude_delta))
            return stop_loss_ratio
            
        except Exception as e:
            logger.error(f"❌ 获取止损比例失败: {e}")
            return -0.10  # 默认止损10%
    
    @staticmethod
    def _get_take_profit_ratio(stop_loss_ratio: float, settings: Dict[str, Any]) -> float:
        """
        获取止盈比例（永远是止损的1.5倍）
        
        Args:
            stop_loss_ratio: 止损比例
            
        Returns:
            float: 止盈比例
        """
        try:
            win_loss_ratio = settings['core']['profit_loss_ratio']
            take_profit_ratio = abs(stop_loss_ratio) * win_loss_ratio
            return take_profit_ratio
            
        except Exception as e:
            logger.error(f"❌ 获取止盈比例失败: {e}")
            return 0.15  # 默认止盈15%
    
