#!/usr/bin/env python3
"""
ReverseTrendBet 策略 - 在平稳段落中寻找突破机会
"""
from typing import Dict, List, Any, Optional
from loguru import logger

from app.analyzer.strategy.RTB.settings import settings
from app.analyzer.analyzer_service import AnalyzerService
from utils.icon.icon_service import IconService
from ...components.base_strategy import BaseStrategy

class ReverseTrendBet(BaseStrategy):
    """ReverseTrendBet 策略实现"""
    
    # 策略启用状态
    is_enabled = True
    
    def __init__(self, db, is_verbose: bool = False):
        super().__init__(
            db=db, 
            is_verbose=is_verbose,
            name="ReverseTrendBet",
            abbreviation="RTB"
        )
        super().initialize()

    # ========================================================
    # Core logic:
    # ========================================================

    @staticmethod
    def scan_opportunity(stock: Dict[str, Any], data: Dict[str, Any], settings: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        扫描单只股票的投资机会 - RTB 超短线策略
        
        策略逻辑：
        1. 当日收盘价刚刚站上5日均线
        2. 周线和月线也都在5日均线以上
        3. 满足以上条件时买入
        
        Args:
            stock: 股票信息
            data: K线数据
            settings: 策略设置
            
        Returns:
            Optional[Dict]: 机会信息或None
        """
        daily_klines = data.get('klines', {}).get('daily', [])
        weekly_klines = data.get('klines', {}).get('weekly', [])
        monthly_klines = data.get('klines', {}).get('monthly', [])
        
        # 检查数据是否充足
        if not daily_klines or len(daily_klines) < 10:
            return None
        if not weekly_klines or len(weekly_klines) < 1:
            return None
        if not monthly_klines or len(monthly_klines) < 1:
            return None
        
        record_of_today = daily_klines[-1]
        record_of_yesterday = daily_klines[-2] if len(daily_klines) >= 2 else None
        latest_weekly = weekly_klines[-1]
        latest_monthly = monthly_klines[-1]
        
        # 获取当日价格和MA5
        today_close = record_of_today.get('close')
        today_ma5 = record_of_today.get('ma5')
        
        if today_close is None or today_ma5 is None:
            return None
        
        # 条件1：当日收盘价站上5日均线
        is_above_ma5_today = today_close > today_ma5
        
        if not is_above_ma5_today:
            return None
        
        # 条件2：前一日收盘价在5日均线下方（刚刚站上）
        if record_of_yesterday:
            yesterday_close = record_of_yesterday.get('close')
            yesterday_ma5 = record_of_yesterday.get('ma5')
            
            if yesterday_close is not None and yesterday_ma5 is not None:
                was_below_ma5_yesterday = yesterday_close <= yesterday_ma5
                
                if not was_below_ma5_yesterday:
                    # 不是"刚刚"站上，而是已经在上方了
                    return None
        
        # 条件3：周线收盘价在5日均线以上
        weekly_close = latest_weekly.get('close')
        if weekly_close is None or weekly_close <= today_ma5:
            return None
        
        # 条件4：月线收盘价在5日均线以上
        monthly_close = latest_monthly.get('close')
        if monthly_close is None or monthly_close <= today_ma5:
            return None
        
        # 条件5：趋势过滤 - 只在上升趋势中操作
        is_uptrend = ReverseTrendBet._check_uptrend(daily_klines, weekly_klines, monthly_klines)
        if not is_uptrend:
            return None
        
        # 条件6：成交量放大 - 站上MA5时应该放量，避免假突破
        is_volume_increased = ReverseTrendBet._check_volume_increase(daily_klines)
        if not is_volume_increased:
            return None
        
        opportunity = BaseStrategy.to_opportunity(
            stock=stock,
            record_of_today=record_of_today,
            extra_fields={
                'ma5': today_ma5,
                'weekly_close': weekly_close,
                'monthly_close': monthly_close,
                'reason': '日线刚站上MA5，周线月线均在MA5上方',
            },
            lower_bound=today_close * 0.98,
            upper_bound=today_close * 1.02,
        )
        
        return opportunity
    
    @staticmethod
    def _check_uptrend(daily_klines: List[Dict[str, Any]], 
                      weekly_klines: List[Dict[str, Any]], 
                      monthly_klines: List[Dict[str, Any]]) -> bool:
        """
        检查是否处于上升趋势
        
        判断标准：
        1. 日线MA5 > MA10 > MA20 (短期均线多头排列)
        2. 周线价格呈上升趋势（最近几周）
        3. 月线价格呈上升趋势（最近几个月）
        
        Args:
            daily_klines: 日线数据
            weekly_klines: 周线数据
            monthly_klines: 月线数据
            
        Returns:
            bool: 是否处于上升趋势
        """
        if not daily_klines or not weekly_klines or not monthly_klines:
            return False
        
        latest_daily = daily_klines[-1]
        
        # 1. 检查日线均线多头排列（MA5 > MA10 > MA20）
        ma5 = latest_daily.get('ma5')
        ma10 = latest_daily.get('ma10')
        ma20 = latest_daily.get('ma20')
        
        if ma5 is None or ma10 is None or ma20 is None:
            return False
        
        # MA5 应该在最上方，MA20 在最下方
        if not (ma5 > ma10 > ma20):
            return False
        
        # 2. 检查周线上升趋势（最近4周）
        if len(weekly_klines) >= 4:
            recent_weekly_closes = [w.get('close') for w in weekly_klines[-4:] if w.get('close') is not None]
            if len(recent_weekly_closes) >= 3:
                weekly_slope = AnalyzerService.get_slope(recent_weekly_closes)
                # 周线斜率应该为正（上升）
                if weekly_slope <= 0:
                    return False
        
        # 3. 检查月线上升趋势（最近3个月）
        if len(monthly_klines) >= 3:
            recent_monthly_closes = [m.get('close') for m in monthly_klines[-3:] if m.get('close') is not None]
            if len(recent_monthly_closes) >= 2:
                monthly_slope = AnalyzerService.get_slope(recent_monthly_closes)
                # 月线斜率应该为正（上升）
                if monthly_slope <= 0:
                    return False
        
        return True
    
    @staticmethod
    def _check_volume_increase(daily_klines: List[Dict[str, Any]], lookback_days: int = 5) -> bool:
        """
        检查当日成交量是否放大
        
        判断标准：
        1. 当日成交量 > 最近5日平均成交量的 1.2 倍
        2. 避免无量突破（假突破）
        
        Args:
            daily_klines: 日线数据
            lookback_days: 回看天数计算平均成交量
            
        Returns:
            bool: 成交量是否放大
        """
        if len(daily_klines) < lookback_days + 1:
            return False
        
        # 获取当日成交量
        today_volume = daily_klines[-1].get('volume')
        if today_volume is None or today_volume == 0:
            # 没有成交量数据，不做限制（容错处理）
            return True
        
        # 获取最近5天的成交量（不包括今天）
        recent_volumes = []
        for kline in daily_klines[-(lookback_days+1):-1]:
            volume = kline.get('volume')
            if volume is not None and volume > 0:
                recent_volumes.append(volume)
        
        if len(recent_volumes) < lookback_days:
            # 成交量数据不足，不做限制
            return True
        
        # 计算平均成交量
        avg_volume = AnalyzerService.get_mean(recent_volumes)
        
        # 当日成交量应该 > 平均成交量的 1.2 倍（放量20%）
        volume_ratio = today_volume / avg_volume if avg_volume > 0 else 0
        
        return volume_ratio >= 1.2
    
    @staticmethod
    def _check_rsi_range(daily_klines: List[Dict[str, Any]]) -> bool:
        """
        检查 RSI 是否在合适的区间且呈上升趋势
        
        判断标准：
        1. RSI 在 30-70 区间内（避免超买和极度弱势）
        2. RSI 呈上升趋势（今天 RSI > 昨天 RSI）- 确保动能向上
        
        Args:
            daily_klines: 日线数据
            
        Returns:
            bool: RSI 是否在合适区间且上升
        """
        if len(daily_klines) < 2:
            return False
        
        today_kline = daily_klines[-1]
        yesterday_kline = daily_klines[-2]
        
        # 获取今天和昨天的 RSI 值
        today_rsi = today_kline.get('rsi')
        yesterday_rsi = yesterday_kline.get('rsi')
        
        if today_rsi is None:
            # 没有 RSI 数据，不做限制（容错处理）
            return True
        
        # 条件1：RSI 应该在 30-70 区间内
        if not (30 <= today_rsi <= 70):
            return False
        
        # 条件2：RSI 呈上升趋势（可选，如果没有昨天的数据就只检查区间）
        if yesterday_rsi is not None:
            if today_rsi <= yesterday_rsi:
                return False
        
        return True