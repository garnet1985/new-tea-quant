from datetime import datetime
from enum import Enum
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
    def to_usable_stock_idx(stock_idx):
        if not stock_idx:
            return []
            
        filtered_idx = []
        
        for stock in stock_idx:
            stock_id = stock.get('id', '')
            stock_name = stock.get('name', '')
            
            # 过滤条件1：排除北交所股票（ID包含BJ）
            avoid_name_starts_with = conf['stock_idx']['avoid_name_starts_with']
            avoid_code_starts_with = conf['stock_idx']['avoid_code_starts_with']
            avoid_exchange_center = conf['stock_idx']['avoid_exchange_center']

            if any(stock_name.startswith(prefix) for prefix in avoid_name_starts_with):
                continue

            if any(stock_id.startswith(prefix) for prefix in avoid_code_starts_with):
                continue

            if any(string in stock_id for string in avoid_exchange_center):
                continue

            # 通过所有过滤条件，添加到结果列表
            filtered_idx.append(stock)
            
        return filtered_idx

    @staticmethod
    def find_valleys(daily_data: list, min_drop_threshold: float = 0.10, 
                     local_range_days: int = 5, lookback_days: int = 60) -> list:
        """
        寻找波谷（通用方法）
        
        Args:
            daily_data: 日线数据列表
            min_drop_threshold: 最小跌幅阈值
            local_range_days: 局部最低点判断范围
            lookback_days: 寻找前期高点的回溯天数
            
        Returns:
            List: 波谷列表
        """
        if not daily_data or len(daily_data) < local_range_days * 2 + 1:
            return []
        
        valleys = []
        
        for i in range(local_range_days, len(daily_data) - local_range_days):
            current_price = daily_data[i]['close']
            
            # 检查是否为局部最低点
            is_local_min = True
            for j in range(i - local_range_days, i + local_range_days + 1):
                if j != i and daily_data[j]['close'] < current_price:
                    is_local_min = False
                    break
            
            if not is_local_min:
                continue
            
            # 寻找前期高点
            left_peak = AnalyzerService._find_left_peak_in_range(daily_data, i, lookback_days)
            if left_peak is None:
                continue
            
            # 计算跌幅
            # 避免除零错误
            if left_peak > 0:
                drop_rate = (left_peak - current_price) / left_peak
            else:
                drop_rate = 0
            
            # 过滤跌幅不足的波谷
            if drop_rate < min_drop_threshold:
                continue
            
            # 找到前期高点的日期
            left_peak_date = AnalyzerService._find_left_peak_date(daily_data, i, lookback_days)
            
            valleys.append({
                'date': daily_data[i]['date'],
                'price': current_price,
                'drop_rate': drop_rate,
                'left_peak': left_peak,
                'left_peak_date': left_peak_date,
                'record': daily_data[i]
            })
        
        return valleys

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