import math
from typing import Dict, List, Any, Tuple
from loguru import logger

from app.analyzer.strategy.HL.HL_entity import HistoricLowEntity
from .settings import settings


class HistoricLowService:
    """HistoricLow策略的静态服务类"""

    @staticmethod
    def split_freeze_and_history_data(daily_records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        分割日线数据为冻结期和历史期
        
        Args:
            daily_data: 完整的日线数据列表
            
        Returns:
            freeze_records: 投资冻结期的数据
            history_records: 可以用来寻找机会的日线数据
        """
        # 获取配置参数
        freeze_days = settings['daily_data_requirements']['freeze_period_days']
        
        # 分割数据
        freeze_records = daily_records[-freeze_days:]  # 最近N个交易日（冻结期）
        history_records = daily_records[:-freeze_days]  # 之前的数据（历史期）
        
        return freeze_records, history_records


    @staticmethod
    def find_low_points(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """寻找历史低点"""
        low_points = []
        target_years = settings['daily_data_requirements']['low_points_ref_years']
        
        if not records:
            return low_points
        
        date_of_today = records[-1]['date']
        
        # 解析今天的日期
        from datetime import datetime, timedelta
        today = datetime.strptime(date_of_today, '%Y%m%d')
        
        for years_back in target_years:
            # 计算时间区间的开始日期（往前推years_back年）
            start_date = today - timedelta(days=years_back * 365)
            start_date_str = start_date.strftime('%Y%m%d')
            
            # 找到该时间区间内的所有记录
            period_records = [record for record in records 
                            if record['date'] >= start_date_str and record['date'] < date_of_today]
            
            if not period_records:
                continue
                
            # 找到该时间区间内的最低价格
            min_record = min(period_records, key=lambda x: float(x['close']))
            
            low_points.append(HistoricLowEntity.to_low_point(years_back, min_record))
        
        return low_points










    
    @staticmethod
    def is_in_invest_range(record_of_today, low_point, freeze_data=None):
        """
        检查是否在投资范围内
        """
        if not record_of_today or not low_point:
            return False
        
        current_price = record_of_today.get('close')
        if not current_price:
            return False
        
        lower_bound = low_point.get('invest_lower_bound')
        upper_bound = low_point.get('invest_upper_bound')
        
        if not lower_bound or not upper_bound:
            return False
        
        return lower_bound <= current_price <= upper_bound
    
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
    def calculate_slope(klines: List[Dict[str, Any]]) -> float:
        """
        计算价格趋势的斜率（角度）
        """
        if not klines or len(klines) < 2:
            return 0.0
        
        # 获取价格数据
        prices = []
        for kline in klines:
            close_price = kline.get('close')
            if close_price and close_price > 0:
                prices.append(close_price)
        
        if len(prices) < 2:
            return 0.0
        
        # 计算线性回归斜率
        n = len(prices)
        x_sum = sum(range(n))
        y_sum = sum(prices)
        xy_sum = sum(i * prices[i] for i in range(n))
        x2_sum = sum(i * i for i in range(n))
        
        # 线性回归公式: slope = (n*xy_sum - x_sum*y_sum) / (n*x2_sum - x_sum^2)
        denominator = n * x2_sum - x_sum * x_sum
        if denominator == 0:
            return 0.0
        
        slope = (n * xy_sum - x_sum * y_sum) / denominator
        
        # 转换为角度
        angle_degrees = math.degrees(math.atan(slope))
        
        return angle_degrees
    
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
    def filter_out_negative_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        过滤掉价格为负或无效的记录
        """
        if not records:
            return []
        
        filtered_records = []
        for record in records:
            close_price = record.get('close', 0)
            if close_price and close_price > 0:
                filtered_records.append(record)
        
        return filtered_records
    