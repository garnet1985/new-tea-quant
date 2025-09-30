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
        扫描单只股票的投资机会 - RTB策略
        
        新逻辑：
        1. 首先找到价格波动较为平稳的段落
        2. 在平稳段落中寻找收盘价站上所有均线的机会
        """


        daily_klines = data.get('klines', {}).get('daily', [])
        if not daily_klines or len(daily_klines) < 60:  # 至少需要60天数据
            return None

        # 1. 检查均线是否收敛
        is_ma_converged = ReverseTrendBet._is_ma_converged(daily_klines)
        if not is_ma_converged:
            return None

        record_of_today = daily_klines[-1]  

        is_close_above_ma5 = ReverseTrendBet._is_close_above_ma(record_of_today, 5)
        is_close_above_ma10 = ReverseTrendBet._is_close_above_ma(record_of_today, 10)

        if not is_close_above_ma5 or not is_close_above_ma10:
            return None

        logger.info(f"{IconService.get('green_dot')} 股票 {stock['name']} ({stock['id']}) 扫描完成, 发现RTB机会: {record_of_today['date']}")
        opportunity = BaseStrategy.to_opportunity(
            stock=stock,
            record_of_today=record_of_today,
            lower_bound=record_of_today['close'] * 0.98,
            upper_bound=record_of_today['close'] * 1.02,
        )
        
        return opportunity

    @staticmethod
    def _is_close_above_ma(record_of_today: Dict[str, Any], ma_days: int) -> bool:
        """
        检查收盘价是否站上指定均线的收盘价
        """
        return record_of_today.get('close') > record_of_today.get(f'ma{ma_days}')
    
    @staticmethod
    def _is_ma_converged(klines: List[Dict[str, Any]]) -> bool:
        """
        检查段落内移动平均线是否收敛
        
        Args:
            klines: K线数据段落
            
        Returns:
            bool: 是否收敛
        """
        conf = settings.get('core', {})
        
        if len(klines) < conf['convergence']['days']:
            return False
        
        # 获取最新的K线数据
        latest_kline = klines[-1]
        
        # 检查是否有移动平均线数据
        ma_fields = [field for field in latest_kline.keys() if field.startswith('ma')]
        if len(ma_fields) < 3:  # 至少需要3条均线
            return False
        
        # 获取所有移动平均线值
        ma_values = []
        for field in ma_fields:
            ma_value = latest_kline.get(field)
            if ma_value is not None:
                ma_values.append(ma_value)
        
        if len(ma_values) < 3:
            return False
        
        # 使用 AnalyzerService 计算均线的统计指标
        mean_ma = AnalyzerService.get_mean(ma_values)
        std = AnalyzerService.get_standard_deviation(ma_values)
        
        # 均线标准差不能超过均价的1%（非常严格）
        if std > mean_ma * 0.01:
            return False
        
        # 检查最大最小均线差距
        max_ma = max(ma_values)
        min_ma = min(ma_values)
        
        # 最大最小均线差距不能超过均价的2%
        if (max_ma - min_ma) > mean_ma * 0.02:
            return False
        
        return True




    
    # @staticmethod
    # def _find_stable_periods(klines: List[Dict[str, Any]], min_period_days: int = 20) -> List[tuple]:
    #     """
    #     寻找价格波动较为平稳的段落
        
    #     Args:
    #         klines: K线数据
    #         min_period_days: 最小平稳段落长度
            
    #     Returns:
    #         List[tuple]: 平稳段落的起止索引列表 [(start_idx, end_idx), ...]
    #     """
    #     if len(klines) < min_period_days:
    #         return []
        
    #     stable_periods = []
    #     current_start = None
        
    #     for i in range(min_period_days, len(klines)):
    #         # 检查从i-min_period_days到i的段落是否平稳
    #         period_klines = klines[i-min_period_days:i+1]
            
    #         if ReverseTrendBet._is_stable_period(period_klines):
    #             if current_start is None:
    #                 current_start = i - min_period_days
    #         else:
    #             # 当前段落不平稳，结束之前的平稳段落
    #             if current_start is not None:
    #                 stable_periods.append((current_start, i-1))
    #                 current_start = None
        
    #     # 处理最后一个平稳段落
    #     if current_start is not None:
    #         stable_periods.append((current_start, len(klines)-1))
        
    #     return stable_periods
    
    # @staticmethod
    # def _is_stable_period(klines: List[Dict[str, Any]]) -> bool:
    #     """
    #     判断一个段落是否平稳
        
    #     更严格的平稳判断标准：
    #     1. 价格波动幅度很小
    #     2. 没有明显的趋势性
    #     3. 移动平均线收敛
    #     4. 价格围绕均线波动
        
    #     Args:
    #         klines: K线数据段落
            
    #     Returns:
    #         bool: 是否平稳
    #     """
    #     if len(klines) < 20:  # 至少需要20天数据
    #         return False
        
    #     # 获取收盘价
    #     closes = [kline.get('close') for kline in klines if kline.get('close') is not None]
    #     if len(closes) < len(klines) * 0.9:  # 至少90%的数据有效
    #         return False
        
    #     # 使用 AnalyzerService 计算价格统计指标
    #     avg_price = AnalyzerService.get_mean(closes)
    #     std = AnalyzerService.get_standard_deviation(closes)
    #     slope = AnalyzerService.get_slope(closes)
        
    #     # 1. 检查价格波动幅度（更严格）
    #     max_price = max(closes)
    #     min_price = min(closes)
    #     price_range = max_price - min_price
        
    #     # 价格波动幅度不能超过平均价格的5%（更严格）
    #     if price_range > avg_price * 0.05:
    #         return False
        
    #     # 2. 检查价格标准差（更严格）
    #     # 标准差不能超过平均价格的2%（更严格）
    #     if std > avg_price * 0.02:
    #         return False
        
    #     # 3. 检查趋势斜率（更严格）
    #     # 斜率不能超过平均值的±0.1%（每天，更严格）
    #     if abs(slope) > avg_price * 0.001:
    #         return False
        
    #     # 4. 检查移动平均线是否收敛
    #     if not ReverseTrendBet._check_ma_convergence_in_period(klines):
    #         return False
        
    #     # 5. 检查价格是否围绕均线波动
    #     if not ReverseTrendBet._check_price_around_ma(klines):
    #         return False
        
    #     return True
    
    # @staticmethod
    # def _check_price_around_ma(klines: List[Dict[str, Any]]) -> bool:
    #     """
    #     检查价格是否围绕均线波动
        
    #     Args:
    #         klines: K线数据段落
            
    #     Returns:
    #         bool: 是否围绕均线波动
    #     """
    #     if len(klines) < 10:
    #         return False
        
    #     # 检查最近10天的数据
    #     recent_klines = klines[-10:]
        
    #     above_ma_count = 0
    #     below_ma_count = 0
        
    #     for kline in recent_klines:
    #         close_price = kline.get('close')
    #         if close_price is None:
    #             continue
            
    #         # 获取MA20作为参考均线
    #         ma20 = kline.get('ma20')
    #         if ma20 is None:
    #             continue
            
    #         if close_price > ma20:
    #             above_ma_count += 1
    #         else:
    #             below_ma_count += 1
        
    #     # 价格应该在均线上下波动，不能长期在均线一侧
    #     # 上下波动次数应该相对均衡
    #     total_count = above_ma_count + below_ma_count
    #     if total_count < 8:  # 至少需要8个有效数据点
    #         return False
        
    #     # 上下波动比例不能过于极端（如90%以上在均线一侧）
    #     above_ratio = above_ma_count / total_count
    #     if above_ratio > 0.8 or above_ratio < 0.2:
    #         return False
        
    #     return True
    
    # @staticmethod
    # def _find_opportunity_in_stable_period(stock: Dict[str, Any], klines: List[Dict[str, Any]], 
    #                                      start_idx: int, end_idx: int) -> Optional[Dict[str, Any]]:
    #     """
    #     在平稳段落中寻找投资机会
        
    #     Args:
    #         stock: 股票信息
    #         klines: K线数据
    #         start_idx: 平稳段落开始索引
    #         end_idx: 平稳段落结束索引
            
    #     Returns:
    #         Optional[Dict]: 机会信息或None
    #     """
    #     # 在平稳段落的最后几天中寻找机会
    #     search_start = max(start_idx, end_idx - 5)  # 在最后5天内寻找
        
    #     for i in range(search_start, end_idx + 1):
    #         kline = klines[i]
    #         current_close = kline.get('close')
    #         current_date = kline.get('date')
            
    #         if not current_close or not current_date:
    #             continue
            
    #         # 检查是否有移动平均线数据
    #         ma_fields = [field for field in kline.keys() if field.startswith('ma')]
    #         if not ma_fields:
    #             continue
            
    #         # 获取所有移动平均线值
    #         ma_values = []
    #         for field in ma_fields:
    #             ma_value = kline.get(field)
    #             if ma_value is not None:
    #                 ma_values.append(ma_value)
            
    #         if not ma_values:
    #             continue
            
    #         # 检查当前收盘价是否站上所有均线
    #         if current_close > max(ma_values):
    #             # 找到机会，打印平稳段落信息
    #             start_date = klines[start_idx].get('date')
    #             # logger.info(f"{IconService.get('info')} 发现平稳段落: {stock.get('name')} ({stock.get('id')})")
    #             # logger.info(f"  平稳段落: {start_date} 到 {current_date}")
    #             # logger.info(f"  段落长度: {end_idx - start_idx + 1} 天")
                
    #             # 计算上下1%的价格浮动
    #             lower_bound = current_close * 0.99
    #             upper_bound = current_close * 1.01
                
    #             # 创建机会对象
    #             opportunity = BaseStrategy.to_opportunity(
    #                 stock=stock,
    #                 record_of_today=kline,
    #                 extra_fields={
    #                     'ma_values': {field: kline.get(field) for field in ma_fields},
    #                     'stable_period_start': start_date,
    #                     'stable_period_end': current_date,
    #                     'stable_period_length': end_idx - start_idx + 1,
    #                     'reason': f'在平稳段落中收盘价{current_close}站上所有均线'
    #                 },
    #                 lower_bound=lower_bound,
    #                 upper_bound=upper_bound,
    #             )
                
    #             logger.info(f"{current_date}: {IconService.get('success')} 发现RTB机会: {stock.get('name')} ({stock.get('id')})")
    #             return opportunity
        
    #     return None

    # @staticmethod
    # def _check_ma_convergence(klines: List[Dict[str, Any]], ma_fields: List[str], lookback_days: int = 20) -> bool:
    #     """
    #     检查移动平均线是否在收敛
        
    #     改进的收敛判断：
    #     1. 标准差必须在减小（趋势收敛）
    #     2. 当前标准差必须小于均价的指定百分比（绝对收敛）
    #     3. 最长期均线（MA60）与最短期均线的差距不能过大
        
    #     Args:
    #         klines: K线数据
    #         ma_fields: 移动平均线字段名列表
    #         lookback_days: 回看天数
            
    #     Returns:
    #         bool: 是否收敛
    #     """
    #     if len(klines) < lookback_days:
    #         return False
        
    #     # 获取最新的K线数据
    #     latest_kline = klines[-1]
        
    #     # 获取最近lookback_days天的数据
    #     recent_klines = klines[-lookback_days:]
        
    #     # 计算每天所有均线的标准差
    #     daily_std = []
    #     for kline in recent_klines:
    #         ma_values = []
    #         for field in ma_fields:
    #             ma_value = kline.get(field)
    #             if ma_value is not None:
    #                 ma_values.append(ma_value)
            
    #         if len(ma_values) >= 2:
    #             # 使用 AnalyzerService 计算标准差
    #             std = AnalyzerService.get_standard_deviation(ma_values)
    #             daily_std.append(std)
        
    #     if len(daily_std) < 10:  # 至少需要10个数据点
    #         return False
        
    #     # 1. 检查标准差是否在减小（趋势收敛）
    #     recent_avg_std = AnalyzerService.get_mean(daily_std[-5:])
    #     earlier_avg_std = AnalyzerService.get_mean(daily_std[-10:-5])
        
    #     if recent_avg_std >= earlier_avg_std:
    #         return False
        
    #     # 2. 检查当前绝对收敛程度
    #     current_ma_values = []
    #     current_close = latest_kline.get('close')
        
    #     for field in ma_fields:
    #         ma_value = latest_kline.get(field)
    #         if ma_value is not None:
    #             current_ma_values.append(ma_value)
        
    #     if len(current_ma_values) < 2 or not current_close:
    #         return False
        
    #     # 使用 AnalyzerService 计算当前均线统计指标
    #     mean_ma = AnalyzerService.get_mean(current_ma_values)
    #     current_std = AnalyzerService.get_standard_deviation(current_ma_values)
        
    #     # 标准差必须小于收盘价的3%（绝对收敛条件）
    #     if current_std > current_close * 0.03:
    #         return False
        
    #     # 3. 检查最长期与最短期均线的差距
    #     max_ma = max(current_ma_values)
    #     min_ma = min(current_ma_values)
        
    #     # 最大最小均线差距不能超过均价的5%
    #     if (max_ma - min_ma) > mean_ma * 0.05:
    #         return False
        
    #     return True

    # @staticmethod
    # def _check_price_stability(klines: List[Dict[str, Any]], lookback_days: int = 10) -> bool:
    #     """
    #     检查价格是否趋于平稳
        
    #     Args:
    #         klines: K线数据
    #         lookback_days: 回看天数
            
    #     Returns:
    #         bool: 是否趋于平稳
    #     """
    #     if len(klines) < lookback_days:
    #         return False
        
    #     # 获取最近lookback_days天的收盘价
    #     recent_closes = []
    #     for kline in klines[-lookback_days:]:
    #         close_price = kline.get('close')
    #         if close_price is not None:
    #             recent_closes.append(close_price)
        
    #     if len(recent_closes) < lookback_days:
    #         return False
        
    #     # 使用 AnalyzerService 计算价格统计指标
    #     mean_price = AnalyzerService.get_mean(recent_closes)
    #     std = AnalyzerService.get_standard_deviation(recent_closes)
        
    #     # 波动率小于均价的2%认为趋于平稳
    #     return std < mean_price * 0.02
    
    # @staticmethod
    # def _check_ma20_slope(klines: List[Dict[str, Any]], lookback_days: int = 10) -> bool:
    #     """
    #     检查MA20斜率不能向下太多
        
    #     Args:
    #         klines: K线数据
    #         lookback_days: 回看天数
            
    #     Returns:
    #         bool: MA20斜率是否可接受（不是大幅向下）
    #     """
    #     if len(klines) < lookback_days:
    #         return False
        
    #     # 获取最近lookback_days天的MA20数据
    #     ma20_values = []
    #     for kline in klines[-lookback_days:]:
    #         ma20_value = kline.get('ma20')
    #         if ma20_value is not None:
    #             ma20_values.append(ma20_value)
        
    #     if len(ma20_values) < lookback_days:
    #         return False
        
    #     # 使用 AnalyzerService 计算MA20的斜率
    #     slope = AnalyzerService.get_slope(ma20_values)
    #     avg_ma20 = AnalyzerService.get_mean(ma20_values)
        
    #     # 斜率不能向下超过平均值的-0.5%（每天）
    #     # 即10天内MA20下降不能超过5%
    #     max_negative_slope = -avg_ma20 * 0.005  # -0.5% per day
        
    #     return slope >= max_negative_slope

    # @staticmethod
    # def _check_gentle_trend(klines: List[Dict[str, Any]], lookback_days: int = 20) -> bool:
    #     """
    #     检查价格是否处于平缓趋势
        
    #     平缓趋势的判断标准：
    #     1. 价格整体趋势不能太陡峭（上升或下降）
    #     2. 价格波动不能太剧烈
    #     3. 价格应该在一个相对稳定的区间内波动
        
    #     Args:
    #         klines: K线数据
    #         lookback_days: 回看天数
            
    #     Returns:
    #         bool: 是否处于平缓趋势
    #     """
    #     if len(klines) < lookback_days:
    #         return False
        
    #     # 获取最近lookback_days天的收盘价
    #     recent_closes = []
    #     for kline in klines[-lookback_days:]:
    #         close_price = kline.get('close')
    #         if close_price is not None:
    #             recent_closes.append(close_price)
        
    #     if len(recent_closes) < lookback_days:
    #         return False
        
    #     # 使用 AnalyzerService 计算价格统计指标
    #     avg_price = AnalyzerService.get_mean(recent_closes)
    #     std = AnalyzerService.get_standard_deviation(recent_closes)
    #     median_price = AnalyzerService.get_median(recent_closes)
    #     price_slope = AnalyzerService.get_slope(recent_closes)
        
    #     # 1. 检查整体趋势斜率（线性回归）
    #     # 价格趋势斜率不能超过平均值的±0.3%（每天）
    #     # 即20天内价格变化不能超过±6%
    #     max_abs_slope = avg_price * 0.003  # ±0.3% per day
        
    #     if abs(price_slope) > max_abs_slope:
    #         return False
        
    #     # 2. 检查价格波动幅度
    #     max_price = max(recent_closes)
    #     min_price = min(recent_closes)
    #     price_range = max_price - min_price
        
    #     # 价格波动幅度不能超过平均价格的15%
    #     if price_range > avg_price * 0.15:
    #         return False
        
    #     # 3. 检查价格是否在相对稳定的区间内
    #     # 标准差不能超过平均价格的5%
    #     if std > avg_price * 0.05:
    #         return False
        
    #     # 4. 检查价格是否围绕某个中心值波动
    #     # 中位数与平均值的差距不能太大
    #     if abs(median_price - avg_price) > avg_price * 0.02:  # 2%
    #         return False
        
    #     return True