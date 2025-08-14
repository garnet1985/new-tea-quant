import pprint
import math
from typing import Dict, List, Any

from loguru import logger
from .strategy_settings import invest_settings
from datetime import datetime


class HistoricLowService:
    def __init__(self):
        pass

    def get_min_required_monthly_records(self):
        return invest_settings['min_required_monthly_records'] + invest_settings['goal']['invest_reference_day_distance_threshold'] / 30 + 1

    def find_lowest_records(self, records):
        """寻找最低点记录 - 参照Node.js版本实现"""
        low_points = []

        if not self.is_reached_min_required_monthly_records(records):
            return []

        # 遍历所有扫描周期
        for term in invest_settings['terms']:
            lowest_record = self.find_lowest_record(records, term)
            if lowest_record:
                low_points.append({
                    'term': term,
                    'record': lowest_record
                })

        # 添加全局最低点（term=0表示所有历史数据）
        # TODO: to be improved: not only low points, but need to see how long it stays at the lowest point
        lowest_record = self.find_lowest_record(records)
        if lowest_record:
            low_points.append({
                'term': 0,
                'record': lowest_record
            })

        return low_points

    def find_lowest_record(self, records, amount=None):
        """寻找指定周期内的最低点记录 - 参照Node.js版本实现"""
        if not records or len(records) == 0:
            return None
        
        # 获取时间距离阈值
        min_days = invest_settings.get('goal').get('invest_reference_day_distance_threshold')
        
        # 计算需要排除的记录数量（最近N天的记录）
        # 假设月度数据，大约30天一条记录
        exclude_count = int(min_days / 30) + 1
        
        lowest_record = None
        
        # 从最新到最旧查找（与JavaScript版本一致）
        # 跳过最近的exclude_count条记录
        for i in range(len(records) - 1 - exclude_count, -1, -1):
            record = records[i]
            
            # 检查记录是否有效
            if record is None or 'lowest' not in record:
                continue
                
            if lowest_record is None or float(record['lowest']) < float(lowest_record['lowest']):
                lowest_record = record
                
            # 如果指定了amount，检查是否达到指定数量
            if amount and (len(records) - i) == amount:
                break
                
        return lowest_record
        
    def find_lowest(self, records):
        """寻找最低点记录（从最新到最旧查找，与JavaScript版本一致）"""
        # 检查输入数据是否有效
        if not records or len(records) == 0:
            return None
            
        lowest_record = None
        # 从最新到最旧查找（与JavaScript版本一致）
        for i in range(len(records) - 1, -1, -1):
            record = records[i]
            # 检查记录是否有效
            if record is None or 'lowest' not in record:
                continue
            if lowest_record is None or record['lowest'] < lowest_record['lowest']:
                lowest_record = record
        return lowest_record

    def is_in_invest_range(self, record, low_point):
        """检查是否在投资范围内"""
        # 检查low_point是否有效
        if low_point is None or low_point['record'] is None:
            return False
            
        # 将Decimal转换为float进行计算
        lowest = float(low_point['record']['lowest'])
        close = float(record['close'])
        
        upper = lowest * (1 + invest_settings['goal']['opportunityRange'])
        # lower = lowest * (1 - invest_settings['goal']['opportunityRange'])
        
        # print(f"      📊 投资范围检查: 最低点={lowest}, 当前价格={close}, 范围=[{lower:.2f}, {upper:.2f}]")

        if close < upper:
            return True
        else:
            return False

    def has_lower_point_in_latest_daily_records(self, low_point: Dict[str, Any], daily_records: List[Dict[str, Any]]) -> bool:
        # 获取历史低点价格
        historic_low_price = float(low_point['record']['close'])
        
        # 计算opportunityRange的下限（下方5%）
        opportunity_range = invest_settings['goal']['opportunityRange']
        lower_bound = historic_low_price * (1 - opportunity_range)
        
        # 检查日线记录中是否有跌破下限的点位
        for record in daily_records:
            daily_low = float(record['close'])
            if daily_low < lower_bound:
                return True
        return False

    def set_loss(self, record):
        return float(record['close']) * invest_settings['goal']['loss']
    
    def set_win(self, record):
        return float(record['close']) * invest_settings['goal']['win']

    def is_reached_min_required_monthly_records(self, records):
        return len(records) >= invest_settings['min_required_monthly_records'] + invest_settings['goal']['invest_reference_day_distance_threshold'] / 30 + 1

    def get_max_required_monthly_records(self):
        return max(invest_settings['terms'])

    def get_k_lines_before_date(self, target_date: str, k_lines: List[Dict[str, Any]]) -> Dict[str, Any]:
        target_datetime = datetime.strptime(target_date, '%Y%m%d')
        left = 0
        right = len(k_lines) - 1
        results = []
        record_of_today = None
        
        while left <= right:
            mid = (left + right) // 2
            current_date = datetime.strptime(k_lines[mid]['date'], '%Y%m%d')
            
            if current_date == target_datetime:
                # 找到匹配的记录
                record_of_today = k_lines[mid]
                results = k_lines[:mid]
                break
            elif current_date < target_datetime:
                # 当前记录在目标日期之前，包含它并向右搜索
                results = k_lines[:mid + 1]
                left = mid + 1
            else:
                # 当前记录在目标日期之后，向左搜索
                right = mid - 1
        
        return results

    def get_investing(self, stock, investing_stocks):
        return investing_stocks.get(stock['id'])


    def is_trend_too_steep(self, frozen_window_daily_data):
        """
        检查趋势是否过于陡峭
        使用回归分析检查最近90条数据的斜率变化和最近10条数据的斜率角度
        
        Args:
            daily_records: 日线数据列表
            
        Returns:
            bool: True表示趋势过于陡峭，False表示趋势合适
        """
        # 获取投资冻结窗口的天数
        threshold_days = invest_settings['goal']['invest_reference_day_distance_threshold']
        
        if not frozen_window_daily_data or len(frozen_window_daily_data) < threshold_days:
            return True  # 数据不足，认为趋势过于陡峭
        
        # 1. 检查整个冻结窗口的回归斜率是否在渐渐变平
        recent_threshold_days = frozen_window_daily_data[-threshold_days:]
        prices_threshold = [float(record['close']) for record in recent_threshold_days]
        
        # 计算整个冻结窗口的整体斜率
        slope_threshold = self._calculate_trend_slope(prices_threshold)
        
        # 2. 检查最近10条数据的回归斜率角度是否超过30度
        recent_10_days = frozen_window_daily_data[-10:]
        prices_10 = [float(record['close']) for record in recent_10_days]
        
        # 计算10天的斜率
        slope_10 = self._calculate_trend_slope(prices_10)
        
        # 将斜率转换为角度（弧度转角度）
        angle_10 = abs(math.atan(slope_10) * 180 / math.pi)
        
        # 3. 判断条件
        # 条件1: 冻结窗口斜率应该相对平缓（绝对值小于0.01，约0.57度）
        slope_threshold_too_steep = abs(slope_threshold) > 0.01
        
        # 条件2: 10天斜率角度不能超过30度
        angle_10_too_steep = angle_10 > 30
        
        # 如果任一条件满足，则认为趋势过于陡峭
        if slope_threshold_too_steep or angle_10_too_steep:
            return True
        
        # 只在趋势合适时输出一条简单日志
        return False

    def _calculate_trend_slope(self, prices: List[float]) -> float:
        """
        计算价格序列的回归斜率
        
        Args:
            prices: 价格列表
            
        Returns:
            float: 回归斜率
        """
        if len(prices) < 2:
            return 0.0
        
        n = len(prices)
        x = list(range(n))  # 时间序列 [0, 1, 2, ..., n-1]
        
        # 计算均值
        x_mean = sum(x) / n
        y_mean = sum(prices) / n
        
        # 计算回归斜率: slope = Σ((x-x_mean)(y-y_mean)) / Σ((x-x_mean)²)
        numerator = sum((x[i] - x_mean) * (prices[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator