import math
from typing import Dict, List, Any, Tuple
from loguru import logger

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
        
        # 兼容旧实现：records 被认为已经裁剪为“历史期”，其最后一天即为冻结期开始前一天
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
            
            low_points.append(HistoricLowService.to_low_point(years_back, min_record))
        
        return low_points

    @staticmethod
    def find_low_points_with_freeze(daily_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        基于“冻结期”严格确定低点搜索的结束日期：
        - 结束日期 = 冻结期开始前一天（即第 len(daily_records) - freeze_days - 1 条记录）
        - 开始日期 = 结束日期往前推 N 年（3/5/8...）
        仅在 [开始日期, 结束日期] 间寻找最低点
        """
        low_points: List[Dict[str, Any]] = []
        if not daily_records:
            return low_points
        freeze_days = settings['daily_data_requirements']['freeze_period_days']
        target_years = settings['daily_data_requirements']['low_points_ref_years']

        # 结束索引 = 冻结期开始前一天
        end_index = max(0, len(daily_records) - freeze_days - 1)
        end_date_str = daily_records[end_index]['date']

        # 解析结束日期
        from datetime import datetime, timedelta
        end_date = datetime.strptime(end_date_str, '%Y%m%d')

        # 仅考虑结束日期之前的数据
        eligible_records = [r for r in daily_records if r['date'] <= end_date_str]
        if not eligible_records:
            return low_points

        for years_back in target_years:
            start_date = end_date - timedelta(days=years_back * 365)
            start_date_str = start_date.strftime('%Y%m%d')

            # 区间过滤（闭区间包含 end_date）
            period_records = [r for r in eligible_records if start_date_str <= r['date'] <= end_date_str]
            if not period_records:
                continue
            min_record = min(period_records, key=lambda x: float(x['close']))
            low_points.append(HistoricLowService.to_low_point(years_back, min_record))

        return low_points
    
    @staticmethod
    def to_low_point(term: int, low_point_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成统一格式的历史低点对象：在 low point record 的基础上，计算出投资范围

        Args:
            term: 历史低点年份
            low_point_record: 历史低点记录

        Returns:
            Dict[str, Any]: 统一格式的历史低点对象
        """

        low_point_config = settings.get('low_point_invest_range')

        if not low_point_config:
            raise Exception("low_point_invest_range is not set in strategy_settings.")

        upper_bound_ratio = low_point_config.get('upper_bound')
        lower_bound_ratio = low_point_config.get('lower_bound')
        min_price_gap = low_point_config.get('min')
        max_price_gap = low_point_config.get('max')

        # 计算绝对价格区间
        upper_absolute_range = low_point_record['close'] * upper_bound_ratio
        lower_absolute_range = low_point_record['close'] * lower_bound_ratio

        # 应用最小/最大限制
        if lower_absolute_range < min_price_gap:
            lower_absolute_range = min_price_gap

        if upper_absolute_range > max_price_gap:
            upper_absolute_range = max_price_gap
        
        # 计算最终的投资范围价格
        upper_bound_price = low_point_record['close'] + upper_absolute_range
        lower_bound_price = low_point_record['close'] - lower_absolute_range

        return {
            'term': term,
            'low_point_price': low_point_record.get('close'),
            'date': low_point_record.get('date'),
            'invest_upper_bound': upper_bound_price,
            'invest_lower_bound': lower_bound_price
        }


    # ========================================================
    @staticmethod
    def is_in_invest_range(record_of_today, low_point):
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
    