from datetime import datetime
from enum import Enum
from typing import Dict, List
from .analyzer_settings import conf

class InvestmentResult(Enum):
    WIN = 'win'
    LOSS = 'loss'
    OPEN = 'open'


class AnalyzerService:
    def __init__(self):
        pass

    @staticmethod
    def get_duration_in_days(start_date: str, end_date: str) -> int:
        start = datetime.strptime(start_date, '%Y%m%d')
        end = datetime.strptime(end_date, '%Y%m%d')
        return (end - start).days
    
    @staticmethod
    def get_annual_return(profit_rate: float, duration_in_days: int) -> float:
        if duration_in_days <= 0:
            return 0.0
        
        # 对于短期投资，使用简单的年化公式：年化收益率 = 总收益率 * (365/投资天数)
        # 这样可以避免短期投资产生极其夸张的年化收益率
        annual_return = profit_rate * (365 / duration_in_days)
        return annual_return

    @staticmethod
    def find_valleys(daily_data: list, min_drop_threshold: float = 0.20, 
                     local_range_days: int = 5, lookback_days: int = 60) -> list:
        """
        寻找波谷（通用方法）
        
        Args:
            daily_data: 日线数据列表
            min_drop_threshold: 在找谷底时，最高点和最低点的最小跌幅
            local_range_days: 判断谷底时的左右范围
            lookback_days: 前N天内的最高点
            
        Returns:
            List: 波谷列表
        """
        if not daily_data or len(daily_data) < local_range_days * 2 + 1:
            return []
        
        valleys = []
        
        for i in range(local_range_days, len(daily_data) - local_range_days):
            current_price = daily_data[i]['close']
            
            # 检查是否为局部最低点
            left_range = daily_data[max(0, i - local_range_days):i]
            right_range = daily_data[i + 1:min(len(daily_data), i + local_range_days + 1)]
            
            if any(r['close'] < current_price for r in left_range + right_range):
                continue
            
            # 寻找前期高点并计算跌幅
            left_peak = AnalyzerService._find_left_peak_in_range(daily_data, i, lookback_days)
            if left_peak is None or left_peak <= 0:
                continue
                
            drop_rate = (left_peak - current_price) / left_peak
            if drop_rate < min_drop_threshold:
                continue
            
            valleys.append({
                'date': daily_data[i]['date'],
                'price': current_price,
                'drop_rate': drop_rate,
                'left_peak': left_peak,
                'left_peak_date': AnalyzerService._find_left_peak_date(daily_data, i, lookback_days),
                'record': daily_data[i]
            })
        
        return valleys

    @staticmethod
    def percentage_based_clustering(num_list: list, threshold_percentage: float = 0.8):
        """
        基于百分比阈值的数值聚类算法
        
        Args:
            num_list: 数值数组，如 [2.47, 2.54, 2.57, ...]
            threshold_percentage: 聚类阈值百分比，默认0.8表示8%
        
        Returns:
            聚类后的组别列表，每个组包含数值和触及次数
        """
        if not num_list:
            return []
        
        # 对数值进行排序
        sorted_values = sorted(num_list)
        groups = []
        current_group = [sorted_values[0]]
        
        for i in range(1, len(sorted_values)):
            current_value = sorted_values[i]
            # 计算与当前组最高值的百分比差异
            group_max = max(current_group)
            percentage_diff = (current_value - group_max) / group_max
            
            # 如果百分比差异小于阈值，加入当前组
            if percentage_diff <= threshold_percentage:
                current_group.append(current_value)
            else:
                # 保存当前组并开始新组
                groups.append({
                    'values': current_group,
                    'min_value': min(current_group),
                    'max_value': max(current_group),
                    'value_span': max(current_group) - min(current_group),
                    'span_percentage': (max(current_group) - min(current_group)) / min(current_group) * 100,
                    'touch_count': len(current_group),
                    'value_range': f"{min(current_group):.2f}-{max(current_group):.2f}"
                })
                current_group = [current_value]
        
        # 添加最后一组
        if current_group:
            groups.append({
                'values': current_group,
                'min_value': min(current_group),
                'max_value': max(current_group),
                'value_span': max(current_group) - min(current_group),
                'span_percentage': (max(current_group) - min(current_group)) / min(current_group) * 100,
                'touch_count': len(current_group),
                'value_range': f"{min(current_group):.2f}-{max(current_group):.2f}"
            })
        
        return groups

    @staticmethod
    def find_peaks(daily_data: list, min_rise_threshold: float = 0.10,
                   local_range_days: int = 5, lookback_days: int = 60) -> list:
        """
        寻找波峰（通用方法）
        
        Args:
            daily_data: 日线数据列表
            min_rise_threshold: 最小涨幅阈值
            local_range_days: 局部最高点判断范围
            lookback_days: 寻找前期低点的回溯天数
            
        Returns:
            List: 波峰列表
        """
        if not daily_data or len(daily_data) < local_range_days * 2 + 1:
            return []
        
        peaks = []
        
        for i in range(local_range_days, len(daily_data) - local_range_days):
            current_price = daily_data[i]['close']
            
            # 检查是否为局部最高点
            is_local_max = True
            for j in range(i - local_range_days, i + local_range_days + 1):
                if j != i and daily_data[j]['close'] > current_price:
                    is_local_max = False
                    break
            
            if not is_local_max:
                continue
            
            # 寻找前期低点
            left_trough = AnalyzerService._find_left_trough_in_range(daily_data, i, lookback_days)
            if left_trough is None:
                continue
            
            # 计算涨幅
            rise_rate = (current_price - left_trough) / left_trough
            
            # 过滤涨幅不足的波峰
            if rise_rate < min_rise_threshold:
                continue
            
            # 找到前期低点的日期
            left_trough_date = AnalyzerService._find_left_trough_date(daily_data, i, lookback_days)
            
            peaks.append({
                'date': daily_data[i]['date'],
                'price': current_price,
                'rise_rate': rise_rate,
                'left_trough': left_trough,
                'left_trough_date': left_trough_date,
                'record': daily_data[i]
            })
        
        return peaks

    @staticmethod
    def _is_local_minimum(data: list, current_idx: int, range_days: int) -> bool:
        """检查是否为局部最低点"""
        if current_idx < range_days or current_idx >= len(data) - range_days:
            return False
        
        current_price = data[current_idx]['close']
        
        for i in range(current_idx - range_days, current_idx + range_days + 1):
            if i != current_idx and data[i]['close'] < current_price:
                return False
        
        return True

    @staticmethod
    def _is_local_maximum(data: list, current_idx: int, range_days: int) -> bool:
        """检查是否为局部最高点"""
        if current_idx < range_days or current_idx >= len(data) - range_days:
            return False
        
        current_price = data[current_idx]['close']
        
        for i in range(current_idx - range_days, current_idx + range_days + 1):
            if i != current_idx and data[i]['close'] > current_price:
                return False
        
        return True

    @staticmethod
    def _find_left_peak_in_range(data: list, current_idx: int, lookback_days: int) -> float:
        """在指定范围内寻找前期最高价"""
        start_idx = max(0, current_idx - lookback_days)
        max_price = float('-inf')
        
        for i in range(start_idx, current_idx):
            if data[i]['close'] > max_price:
                max_price = data[i]['close']
        
        return max_price if max_price != float('-inf') else None

    @staticmethod
    def _find_left_trough_in_range(data: list, current_idx: int, lookback_days: int) -> float:
        """在指定范围内寻找前期最低价"""
        start_idx = max(0, current_idx - lookback_days)
        min_price = float('inf')
        
        for i in range(start_idx, current_idx):
            if data[i]['close'] < min_price:
                min_price = data[i]['close']
        
        return min_price if min_price != float('inf') else None

    @staticmethod
    def _find_left_peak_date(data: list, current_idx: int, lookback_days: int) -> str:
        """在指定范围内寻找前期最高价的日期"""
        start_idx = max(0, current_idx - lookback_days)
        max_price = float('-inf')
        max_date = None
        
        for i in range(start_idx, current_idx):
            if data[i]['close'] > max_price:
                max_price = data[i]['close']
                max_date = data[i]['date']
        
        return max_date

    @staticmethod
    def _find_left_trough_date(data: list, current_idx: int, lookback_days: int) -> str:
        """在指定范围内寻找前期最低价的日期"""
        start_idx = max(0, current_idx - lookback_days)
        min_price = float('inf')
        min_date = None
        
        for i in range(start_idx, current_idx):
            if data[i]['close'] < min_price:
                min_price = data[i]['close']
                min_date = data[i]['date']
        
        return min_date