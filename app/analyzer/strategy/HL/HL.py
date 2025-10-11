#!/usr/bin/env python3
"""
HistoricLow 策略 - 寻找股票的历史低点，识别可能的买入机会
"""
from typing import Dict, List, Any, Optional
from loguru import logger

from app.analyzer.analyzer_service import AnalyzerService
from app.analyzer.strategy.HL.HL_service import HistoricLowService
from ...components.base_strategy import BaseStrategy
from .settings import settings
from utils.icon.icon_service import IconService

class HistoricLow(BaseStrategy):
    """HistoricLow 策略实现"""
    
    def __init__(self, db, is_verbose: bool = False):
        super().__init__(
            db=db, 
            is_verbose=is_verbose,
            name="HistoricLow",
            abbreviation="HL"
        )
        super().initialize()
        
    # ========================================================
    # Core API: Scan opportunity
    # ========================================================
    @staticmethod
    def scan_opportunity(stock: Dict[str, Any], data: List[Dict[str, Any]], settings: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """扫描单只股票的投资机会"""
        daily_klines = data.get('klines', {}).get('daily', [])
        
        # 分割数据为冻结期和历史期
        freeze_records, history_records = HistoricLowService.split_freeze_and_history_data(daily_klines)
        
        # 寻找历史低点：结束日为冻结期开始前一日
        low_points = HistoricLowService.find_low_points(daily_klines)
        
        # 从低点中寻找投资机会
        opportunity = HistoricLow._find_opportunity_from_low_points(stock, low_points, freeze_records, history_records)
        
        return opportunity

    @staticmethod
    def _find_opportunity_from_low_points(stock: Dict[str, Any], low_points: List[Dict[str, Any]], freeze_data: List[Dict[str, Any]], history_data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """从历史低点中寻找投资机会（恢复风控过滤：跌停/新低/振幅/斜率）"""
        if not low_points or not freeze_data:
            return None

        record_of_today = freeze_data[-1]

        # 风控过滤（与旧算法一致的语义）：
        # 1) 不处于连续跌停
        if not HistoricLow.is_out_of_continuous_limit_down(freeze_data):
            return None
        # 2) 冻结期无新低
        if not HistoricLow.has_no_new_low_during_freeze(freeze_data):
            return None
        # 3) 振幅足够
        if not HistoricLow.is_amplitude_sufficient(freeze_data):
            return None
        # 4) 斜率不过陡（满足上升/止跌的斜率阈值）
        if not HistoricLow.is_slope_sufficient(freeze_data):
            return None

        # 核心入场条件：当前价位位于以历史低点为参考的投资区间内
        for low_point in low_points:
            if HistoricLowService.is_in_invest_range(record_of_today, low_point):
                opportunity = BaseStrategy.to_opportunity(
                    stock=stock,
                    record_of_today=record_of_today,
                    extra_fields={
                        'low_point_ref': low_point,
                    },
                    lower_bound=low_point.get('invest_lower_bound'),
                    upper_bound=low_point.get('invest_upper_bound'),
                )
                return opportunity

        return None

    @staticmethod
    def is_out_of_continuous_limit_down(freeze_data: List[Dict[str, Any]]) -> bool:
        """
        检查是否不在连续跌停状态
        """
        if not freeze_data or len(freeze_data) < 2:
            return True
        
        # 检查是否有连续2天以上的大幅下跌（>9.5%）
        consecutive_drops = 0
        max_consecutive_drops = 0
        
        for i in range(1, len(freeze_data)):
            prev_close = freeze_data[i-1].get('close', 0)
            curr_close = freeze_data[i].get('close', 0)
            
            if prev_close > 0 and curr_close > 0:
                drop_rate = (prev_close - curr_close) / prev_close
                
                if drop_rate > 0.095:  # 跌幅超过9.5%
                    consecutive_drops += 1
                    max_consecutive_drops = max(max_consecutive_drops, consecutive_drops)
                else:
                    consecutive_drops = 0
        
        # 如果连续跌停超过1天，则认为在连续跌停状态
        return max_consecutive_drops <= 1

    @staticmethod
    def has_no_new_low_during_freeze(freeze_data):
        """
        检查冻结期内是否有新低
        """
        if not freeze_data or len(freeze_data) < 2:
            return True
        
        # 排除今天的数据
        freeze_data_except_today = freeze_data[:-1]
        if not freeze_data_except_today:
            return True
        
        # 获取冻结期内的最低价
        min_price = min(record.get('close', float('inf')) for record in freeze_data_except_today)
        
        # 获取历史低点价格
        low_point_price = freeze_data_except_today[0].get('low_point_price')
        if not low_point_price:
            return True
        
        # 比较最低价和历史低点价格
        return min_price >= low_point_price

    @staticmethod
    def is_amplitude_sufficient(freeze_data: List[Dict[str, Any]]) -> bool:
        """
        检查振幅是否足够
        """
        if not freeze_data or len(freeze_data) < 2:
            return False
        
        min_amplitude = settings.get('amplitude_filter', {}).get('min_amplitude', 0.1)
        
        # 计算冻结期内的振幅
        prices = [record.get('close', 0) for record in freeze_data if record.get('close')]
        if len(prices) < 2:
            return False
        
        min_price = min(prices)
        max_price = max(prices)
        
        if min_price <= 0:
            return False
        
        amplitude = (max_price - min_price) / min_price
        return amplitude >= min_amplitude

    @staticmethod
    def is_slope_sufficient(freeze_data: List[Dict[str, Any]]) -> bool:
        """
        检查斜率是否足够（不是太陡峭）
        """
        if not freeze_data or len(freeze_data) < 2:
            return False
        
        slope = HistoricLowService.calculate_slope(freeze_data)
        max_slope_degrees = settings.get('slope_check', {}).get('max_slope_degrees', -45.0)
        
        return slope >= max_slope_degrees


    @staticmethod
    def report(opportunities: List[Dict[str, Any]]) -> None:
        """
        呈现扫描/模拟结果 - 可选重写
        
        Args:
            opportunities: 扫描阶段的投资机会列表（scan 使用）
            stock_summaries: 模拟阶段的按股票汇总（simulate 使用，可选）
        """
        for opportunity in opportunities:
            logger.info(f"="*80)
            logger.info(f"股票 {opportunity['stock']['name']} ({opportunity['stock']['id']})")
            logger.info(f"="*80)
            logger.info(f"扫描日期: {opportunity['date']}")
            logger.info(f"当前价格: {opportunity['price']}")
            logger.info(f"机会价格区间: {round(opportunity['lower_bound'], 2)} - {round(opportunity['upper_bound'], 2)}")
            position = AnalyzerService.to_percent(opportunity['price'] - opportunity['lower_bound'], (opportunity['upper_bound'] - opportunity['lower_bound']))
            
            icon = ""
            if position > 90:
                icon = IconService.get('red_dot')
            elif position > 75:
                icon = IconService.get('orange_dot')
            elif position > 60:
                icon = IconService.get('yellow_dot')
            else:
                icon = IconService.get('green_dot')
            
            logger.info(f"当前价格在区间位置: {icon} {position}%")

            low_point_ref = opportunity['extra_fields'].get('low_point_ref', {})
            logger.info(f"参考低点: {low_point_ref.get('date', '无') } 期数：{low_point_ref.get('term')} 价格：{round(low_point_ref.get('low_point_price', '无'), 2)}")
            logger.info(f"="*80)
        return None