import pprint
import math
from typing import Dict, List, Any, Tuple

from loguru import logger
from .strategy_settings import strategy_settings as invest_settings
from app.analyzer.analyzer_service import AnalyzerService
from datetime import datetime


class HistoricLowService:
    def __init__(self):
        pass

    def is_in_invest_range(self, record, low_point):
        """
        检查是否在投资范围内（基于低点价格区间），并防止买在顶上
        
        Args:
            record: 当前交易记录
            low_point: 低点信息，包含price_range
            
        Returns:
            bool: 是否在投资范围内
        """
        # 检查low_point是否有效
        if low_point is None or 'price_range' not in low_point:
            return False
            
        current_price = float(record['close'])
        price_range = low_point['price_range']
        range_min = float(price_range['min'])
        range_max = float(price_range['max'])
        
        # 基本范围检查
        if not (range_min <= current_price <= range_max):
            return False
        
        # 防止买在顶上：检查当前价格在区间中的位置
        # 如果当前价格接近区间上限（超过80%），则避免买入
        price_position_in_range = (current_price - range_min) / (range_max - range_min)
        if price_position_in_range > 0.8:
            return False
        
        return True
    
    def get_previous_low_points(self, record, all_historic_lows):
        """
        获取在指定记录之前出现的历史低价点
        
        Args:
            record: 当前交易记录
            all_historic_lows: 所有历史低点列表
            
        Returns:
            List: 之前出现的低价点列表，按价格从低到高排序
        """
        if not all_historic_lows:
            return []
        
        current_date = record['date']
        previous_lows = []
        
        for low_point in all_historic_lows:
            low_date = low_point['lowest_date']
            low_price = float(low_point['lowest_price'])
            
            # 如果低点日期早于当前记录日期，则认为是之前出现的
            if low_date < current_date:
                previous_lows.append({
                    'price': low_price,
                    'date': low_date,
                    'price_range': low_point['price_range']
                })
        
        # 按价格从低到高排序
        previous_lows.sort(key=lambda x: x['price'])
        
        return previous_lows

    def calculate_investment_targets(self, record, low_point):
        """
        计算投资目标价格（止损和止盈）
        
        Args:
            record: 当前交易记录
            low_point: 低点信息，包含price_range
            
        Returns:
            Dict: 包含止损价和止盈价
        """
        if low_point is None or 'price_range' not in low_point:
            return None
            
        current_price = float(record['close'])
        price_range = low_point['price_range']
        range_min = float(price_range['min'])
        
        # 计算距离下端的价格差和百分比
        price_buffer = current_price - range_min
        buffer_percentage = price_buffer / range_min
        
        # 最小buffer为5%
        min_buffer_percentage = 0.05
        if buffer_percentage < min_buffer_percentage:
            buffer_percentage = min_buffer_percentage
        
        # 计算止损价（当前价格减去buffer）
        stop_loss_price = current_price - (range_min * buffer_percentage)
        
        # 计算止盈价（止损的2倍）
        take_profit_price = current_price + (range_min * buffer_percentage * 2)
        
        return {
            'entry_price': current_price,
            'stop_loss_price': round(stop_loss_price, 2),
            'take_profit_price': round(take_profit_price, 2),
            'buffer_percentage': round(buffer_percentage * 100, 2),
            'stop_loss_percentage': round(buffer_percentage * 100, 2),
            'take_profit_percentage': round(buffer_percentage * 200, 2)
        }

    def should_stop_loss(self, current_price: float, entry_price: float, 
                         price_range_min: float, buffer_percentage: float = 0.03) -> bool:
        """
        判断是否应该止损（百分比缓冲机制）
        
        Args:
            current_price: 当前价格
            entry_price: 入场价格
            price_range_min: 价格区间下限
            buffer_percentage: 缓冲带百分比（默认3%）
            
        Returns:
            bool: 是否应该止损
        """
        # 计算缓冲带下限（区间下限下方增加缓冲带）
        buffer_zone_bottom = price_range_min * (1 - buffer_percentage)
        
        # 如果价格跌破缓冲带下限，触发止损
        if current_price < buffer_zone_bottom:
            return True
        
            return False

    def calculate_percentage_buffer_stop_loss(self, entry_price: float, price_range_min: float,
                                            buffer_percentage: float = 0.03) -> dict:
        """
        计算百分比缓冲止损参数
        
        Args:
            entry_price: 入场价格
            price_range_min: 价格区间下限
            buffer_percentage: 缓冲带百分比（默认3%）
            
        Returns:
            Dict: 百分比缓冲止损参数
        """
        # 计算距离下端的价格差和百分比
        price_buffer = entry_price - price_range_min
        entry_buffer_percentage = max(price_buffer / price_range_min, 0.05)  # 最小5%
        
        # 基础止损价（入场价格减去buffer）
        base_stop_loss = entry_price - (price_range_min * entry_buffer_percentage)
        
        # 缓冲带下限（跌破这个价格才止损）
        buffer_zone_bottom = price_range_min * (1 - buffer_percentage)
        
        # 缓冲带宽度
        buffer_zone_width = price_range_min * buffer_percentage
        
        return {
            'entry_price': round(entry_price, 2),
            'base_stop_loss': round(base_stop_loss, 2),
            'buffer_zone_bottom': round(buffer_zone_bottom, 2),
            'buffer_zone_width': round(buffer_zone_width, 2),
            'entry_buffer_percentage': round(entry_buffer_percentage * 100, 2),
            'buffer_percentage': round(buffer_percentage * 100, 2),
            'price_range_min': round(price_range_min, 2)
        }

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



    def is_reached_min_required_daily_records(self, daily_records):
        """
        检查是否达到最小所需日线记录数
        
        新逻辑：需要至少2000条日线记录
        """
        return len(daily_records) >= invest_settings['daily_data_requirements']['min_required_daily_records']



    def get_k_lines_before_date(self, target_date: str, k_lines: List[Dict[str, Any]]) -> Dict[str, Any]:
        target_datetime = datetime.strptime(target_date, '%Y%m%d')
        left = 0
        right = len(k_lines) - 1
        results = []
        
        while left <= right:
            mid = (left + right) // 2
            current_date = datetime.strptime(k_lines[mid]['date'], '%Y%m%d')
            
            if current_date == target_datetime:
                # 找到匹配的记录
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
        # 获取冻结期天数
        threshold_days = invest_settings['daily_data_requirements']['freeze_period_days']
        
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







    def find_frequently_touched_valleys(self, daily_data: List[Dict[str, Any]], 
                                      price_tolerance: float = 0.05,
                                      min_touch_count: int = 3) -> List[Dict[str, Any]]:
        """
        寻找被多次触及的波谷（高频触及波谷）
        
        Args:
            daily_data: 日线数据列表
            price_tolerance: 价格容忍度（默认5%）
            min_touch_count: 最小触及次数（默认3次）
            
        Returns:
            List[Dict]: 高频触及波谷列表
        """
        # 先找到所有波谷
        all_valleys = AnalyzerService.find_valleys(daily_data)
        if not all_valleys:
            return []
        
        # 按价格分组，寻找价格相近的波谷
        valley_groups = []
        used_indices = set()
        
        for i, valley in enumerate(all_valleys):
            if i in used_indices:
                continue
            
            # 创建新组
            group = [valley]
            used_indices.add(i)
            
            # 寻找价格相近的其他波谷
            for j, other_valley in enumerate(all_valleys[i+1:], i+1):
                if j in used_indices:
                    continue
                
                # 计算价格差异百分比
                price_diff = abs(valley['price'] - other_valley['price']) / valley['price']
                
                if price_diff <= price_tolerance:
                    group.append(other_valley)
                    used_indices.add(j)
            
            # 如果组内波谷数量足够，添加到结果中
            if len(group) >= min_touch_count:
                # 计算组的统计信息
                group_prices = [v['price'] for v in group]
                group_dates = [v['date'] for v in group]
                group_drops = [v['drop_rate'] for v in group]
                
                valley_groups.append({
                    'touch_count': len(group),
                    'price_range': {
                        'min': min(group_prices),
                        'max': max(group_prices),
                        'avg': sum(group_prices) / len(group_prices)
                    },
                    'date_range': {
                        'earliest': min(group_dates),
                        'latest': max(group_dates)
                    },
                    'drop_range': {
                        'min': min(group_drops),
                        'max': max(group_drops),
                        'avg': sum(group_drops) / len(group_drops)
                    },
                    'valleys': group,
                    'strength_score': len(group) * (sum(group_drops) / len(group_drops))  # 触及次数 * 平均跌幅
                })
        
        # 按强度分数排序（触及次数多且跌幅大的排在前面）
        valley_groups.sort(key=lambda x: x['strength_score'], reverse=True)
        
        return valley_groups







    def find_price_level_support_resistance(self, daily_data: List[Dict[str, Any]], 
                                         price_tolerance: float = 0.10,
                                         min_touch_count: int = 3) -> List[Dict[str, Any]]:
        """
        寻找价格区间支撑位（仅波谷触及，谷顶作为辅助信息）
        
        Args:
            daily_data: 日线数据列表
            price_tolerance: 价格容忍度（默认10%）
            min_touch_count: 最小触及次数（默认3次）
            
        Returns:
            List[Dict]: 价格区间支撑位列表
        """
        # 找到所有波谷和顶点
        valleys = AnalyzerService.find_valleys(daily_data)
        peaks = AnalyzerService.find_peaks(daily_data)
        
        if not valleys:
            return []
        
        # 只使用波谷作为主要触及点
        all_touches = []
        
        # 添加波谷触及（主要选择）
        for valley in valleys:
            all_touches.append({
                'type': 'valley',
                'date': valley['date'],
                'price': valley['price'],
                'data': valley
            })
        
        # 谷顶只作为辅助信息，不参与低点选择
        peak_prices = [peak['price'] for peak in peaks] if peaks else []
        
        # 按价格分组
        price_groups = []
        used_indices = set()
        
        for i, touch in enumerate(all_touches):
            if i in used_indices:
                continue
            
            # 创建新组
            group = [touch]
            used_indices.add(i)
            
            # 寻找价格相近的其他触及点
            for j, other_touch in enumerate(all_touches[i+1:], i+1):
                if j in used_indices:
                    continue
                
                # 计算价格差异百分比
                price_diff = abs(touch['price'] - other_touch['price']) / touch['price']
                
                if price_diff <= price_tolerance:
                    group.append(other_touch)
                    used_indices.add(j)
            
            # 如果组内触及点数量足够，添加到结果中
            if len(group) >= min_touch_count:
                # 只统计波谷数量（因为现在all_touches中只有波谷）
                valley_count = len(group)
                
                # 计算组的统计信息
                group_prices = [t['price'] for t in group]
                group_dates = [t['date'] for t in group]
                
                # 检查该价格区间是否有谷顶触及（辅助信息）
                price_min = min(group_prices)
                price_max = max(group_prices)
                peak_touches = [p for p in peak_prices if price_min <= p <= price_max]
                peak_count = len(peak_touches)
                
                price_groups.append({
                    'touch_count': len(group),
                    'valley_count': valley_count,
                    'peak_count': peak_count,  # 谷顶触及次数（辅助信息）
                    'price_range': {
                        'min': min(group_prices),
                        'max': max(group_prices),
                        'avg': sum(group_prices) / len(group_prices)
                    },
                    'date_range': {
                        'earliest': min(group_dates),
                        'latest': max(group_dates)
                    },
                    'touches': group,
                    'strength_score': len(group) * (valley_count + peak_count * 0.3)  # 波谷权重更高，谷顶权重降低
                })
        
        # 按强度分数排序
        price_groups.sort(key=lambda x: x['strength_score'], reverse=True)
        
        return price_groups

    def find_consolidation_valleys(self, daily_data: List[Dict[str, Any]], 
                                 consolidation_days: int = 20,
                                 price_tolerance: float = 0.08,
                                 min_touch_count: int = 3) -> List[Dict[str, Any]]:
        """
        寻找波谷附近有横盘整理的谷底
        
        Args:
            daily_data: 日线数据列表
            consolidation_days: 横盘确认天数（默认20天）
            price_tolerance: 价格容忍度（默认8%）
            min_touch_count: 横盘期间最小触及次数（默认3次）
            
        Returns:
            List[Dict]: 横盘确认波谷列表
        """
        # 先找到所有波谷
        all_valleys = AnalyzerService.find_valleys(daily_data)
        if not all_valleys:
            return []
        
        # 按日期排序
        sorted_data = sorted(daily_data, key=lambda x: x['date'])
        
        consolidation_valleys = []
        
        for valley in all_valleys:
            valley_date = valley['date']
            valley_price = float(valley['price'])  # 转换为float类型
            
            # 通过日期找到波谷在排序数据中的索引
            valley_idx = None
            for i, record in enumerate(sorted_data):
                if record['date'] == valley_date:
                    valley_idx = i
                    break
            
            if valley_idx is None:
                continue
            
            # 检查波谷后的横盘整理
            consolidation_info = self._check_consolidation_after_valley(
                sorted_data, valley_idx, valley_price, 
                consolidation_days, price_tolerance, min_touch_count
            )
            
            if consolidation_info:
                consolidation_valleys.append({
                    'valley': valley,
                    'consolidation': consolidation_info,
                    'consolidation_score': consolidation_info['touch_count'] * consolidation_info['duration_days']
                })
        
        # 按横盘确认分数排序
        consolidation_valleys.sort(key=lambda x: x['consolidation_score'], reverse=True)
        
        return consolidation_valleys

    def _check_consolidation_after_valley(self, sorted_data: List[Dict[str, Any]], 
                                        valley_idx: int, valley_price: float,
                                        consolidation_days: int, price_tolerance: float, 
                                        min_touch_count: int) -> Dict[str, Any]:
        """
        检查波谷后的横盘整理
        
        Args:
            sorted_data: 排序后的数据
            valley_idx: 波谷索引
            valley_price: 波谷价格
            consolidation_days: 横盘确认天数
            price_tolerance: 价格容忍度
            min_touch_count: 最小触及次数
            
        Returns:
            Dict: 横盘信息，如果没有横盘则返回None
        """
        if valley_idx + consolidation_days >= len(sorted_data):
            return None
        
        # 获取波谷后的数据
        after_valley_data = sorted_data[valley_idx + 1:valley_idx + consolidation_days + 1]
        
        # 计算价格区间
        upper_bound = valley_price * (1 + price_tolerance)
        lower_bound = valley_price * (1 - price_tolerance)
        
        # 统计横盘期间的价格触及情况
        touches = []
        consolidation_prices = []
        
        for record in after_valley_data:
            high_price = float(record['highest'])
            low_price = float(record['close'])
            
            # 检查是否触及波谷价格区间
            if low_price <= upper_bound and high_price >= lower_bound:
                touches.append({
                    'date': record['date'],
                    'high': high_price,
                    'low': low_price,
                    'close': float(record['close'])
                })
                consolidation_prices.append(float(record['close']))
        
        # 如果触及次数不够，返回None
        if len(touches) < min_touch_count:
            return None
        
        # 计算横盘统计信息
        if consolidation_prices:
            price_volatility = (max(consolidation_prices) - min(consolidation_prices)) / valley_price
            avg_price = sum(consolidation_prices) / len(consolidation_prices)
            
            return {
                'duration_days': consolidation_days,
                'touch_count': len(touches),
                'price_range': {
                    'upper': upper_bound,
                    'lower': lower_bound,
                    'volatility': price_volatility,
                    'avg_price': avg_price
                },
                'touches': touches,
                'consolidation_quality': self._calculate_consolidation_quality(touches, valley_price)
            }
        
        return None

    def _calculate_consolidation_quality(self, touches: List[Dict], valley_price: float) -> str:
        """
        计算横盘质量
        
        Args:
            touches: 触及记录列表
            valley_price: 波谷价格
            
        Returns:
            str: 横盘质量评级
        """
        if not touches:
            return "未知"
        
        # 计算价格稳定性
        prices = [t['close'] for t in touches]
        price_std = (max(prices) - min(prices)) / valley_price
        
        # 计算触及频率
        touch_frequency = len(touches) / len(touches)  # 这里可以优化
        
        if price_std < 0.05 and len(touches) >= 5:
            return "优秀"
        elif price_std < 0.08 and len(touches) >= 4:
            return "良好"
        elif price_std < 0.12 and len(touches) >= 3:
            return "一般"
        else:
            return "较差"

    def split_daily_data_for_analysis(self, daily_data: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        分割日线数据为冻结期和历史期
        
        Args:
            daily_data: 完整的日线数据列表
            
        Returns:
            Dict: 包含冻结期和历史期数据的分割结果
        """
        # 获取配置参数
        freeze_days = invest_settings['daily_data_requirements']['freeze_period_days']
        
        # 分割数据
        freeze_records = daily_data[-freeze_days:]  # 最近200个交易日（冻结期）
        history_records = daily_data[:-freeze_days]  # 之前的数据（历史期）

        return freeze_records, history_records

    def find_historic_lows(self, history_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        在历史K线数据中寻找历史低点（使用新的低点检测算法）
        
        Args:
            history_data: 历史期日线数据列表
            
        Returns:
            List: 历史低点列表
        """
        if not history_data or len(history_data) < 100:
            return []
        
        # 使用新的低点检测算法
        merged_lows = self.find_merged_historic_lows(history_data)
        
        # 转换为旧格式以保持兼容性
        low_points = []
        for low_point in merged_lows:
            low_points.append({
                'record': low_point['record'],
                'period_name': 'merged_historic_low',
                'trading_days': len(history_data),
                'lowest_price': low_point['price'],
                'lowest_date': low_point['date'],
                'price_range': low_point.get('price_range', {}),
                'conclusion_from': low_point.get('conclusion_from', []),
                'drop_rate': low_point.get('drop_rate', 0),
                'left_peak': low_point.get('left_peak', 0),
                'left_peak_date': low_point.get('left_peak_date', '')
            })
        
        return low_points



    def find_deepest_valley(self, daily_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        找到最深波谷 - 基于find_valleys的结果
        
        Args:
            daily_data: 日线数据列表
            
        Returns:
            Dict: 最深波谷信息，如果没有找到则返回None
        """
        valleys = AnalyzerService.find_valleys(daily_data)
        
        if not valleys:
            return None
        
        # 找到价格最低的波谷
        deepest_valley = min(valleys, key=lambda x: x['price'])
        
        return {
            'record': deepest_valley['record'],
            'period_name': 'deepest_valley',
            'trading_days': len(daily_data),
            'lowest_price': deepest_valley['price'],
            'lowest_date': deepest_valley['date'],
            'drop_rate': deepest_valley['drop_rate'],
            'left_peak': deepest_valley['left_peak'],
            'left_peak_date': deepest_valley['left_peak_date']
        }

    def _check_downtrend(self, data: List[Dict[str, Any]], current_idx: int, days: int) -> bool:
        """检查左侧是否有连续下跌趋势"""
        if current_idx < days:
            return False
        
        for i in range(current_idx - days + 1, current_idx):
            if float(data[i]['close']) <= float(data[i + 1]['close']):
                return False
        return True

    def _check_uptrend(self, data: List[Dict[str, Any]], current_idx: int, days: int) -> bool:
        """检查右侧是否有连续上涨趋势（确认波谷）"""
        if current_idx + days >= len(data):
            return False
        
        for i in range(current_idx, current_idx + days):
            if float(data[i]['close']) >= float(data[i + 1]['close']):
                return False
        return True

    def _find_left_peak(self, data: List[Dict[str, Any]], current_idx: int, days: int) -> float:
        """找到左侧的高点"""
        if current_idx < days:
            return None
        
        left_section = data[current_idx - days:current_idx]
        peak_price = max(float(record['highest']) for record in left_section)
        return peak_price

    def find_merged_historic_lows(self, daily_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        整合三种波谷检测方法，找到综合的历史低点
        
        Args:
            daily_data: 日线数据列表
            
        Returns:
            List[Dict]: 合并后的历史低点列表，每个点包含来源标记
        """
        if not daily_data or len(daily_data) < 100:
            return []
        
        # 1. 找到最深波谷（整个历史的最低点）
        deepest_valley = self.find_deepest_valley(daily_data)
        
        # 2. 找到高频触及的低点（每组多次触及中的最低点）
        frequently_touched = self.find_frequently_touched_valleys(
            daily_data, 
            price_tolerance=0.04,  # 进一步降低价格容忍度，从6%到4%
            min_touch_count=3      # 提高最小触及次数，从2次到3次，减少噪声
        )
        
        # 3. 找到横盘确认的低点（每个横盘期间的最低点）
        consolidation_valleys = self.find_consolidation_valleys(
            daily_data, 
            consolidation_days=25,  # 提高横盘确认天数，从20天到25天，更严格
            price_tolerance=0.03,  # 进一步降低价格容忍度，从4%到3%
            min_touch_count=3      # 提高最小触及次数，从2次到3次，减少噪声
        )
        
        # 4. 找到价格区间支撑位（仅波谷触及，谷顶作为辅助信息）
        price_level_support = self.find_price_level_support_resistance(
            daily_data,
            price_tolerance=0.02,  # 进一步降低价格容忍度，从3%到2%
            min_touch_count=4      # 提高最小触及次数，从3次到4次，更严格
        )
        
        # 5. 收集所有低点，按价格去重
        merged_lows = {}
        
        # 处理最深波谷
        if deepest_valley:
            price_key = f"{deepest_valley['lowest_price']:.3f}"  # 用价格作为key去重，保留3位小数，提高精度
            if price_key not in merged_lows:
                merged_lows[price_key] = {
                    'date': deepest_valley['lowest_date'],
                    'price': round(deepest_valley['lowest_price'], 2),
                    'drop_rate': round(deepest_valley['drop_rate'], 2),
                    'left_peak': round(deepest_valley['left_peak'], 2),
                    'left_peak_date': deepest_valley['left_peak_date'],
                    'conclusion_from': [],
                    'record': deepest_valley['record']
                }
            merged_lows[price_key]['conclusion_from'].append('deepest_valley')
        
        # 处理高频触及的低点
        for group in frequently_touched:
            # 从每组中找出最低价格的点
            lowest_in_group = min(group['valleys'], key=lambda x: x['price'])
            price_key = f"{lowest_in_group['price']:.3f}"  # 提高精度到3位小数
            

            
            if price_key not in merged_lows:
                merged_lows[price_key] = {
                    'date': lowest_in_group['date'],
                    'price': round(lowest_in_group['price'], 2),
                    'drop_rate': round(lowest_in_group['drop_rate'], 2),
                    'left_peak': round(lowest_in_group['left_peak'], 2),
                    'left_peak_date': lowest_in_group['left_peak_date'],
                    'conclusion_from': [],
                    'record': lowest_in_group['record']
                }
            merged_lows[price_key]['conclusion_from'].append('multiple_touches')
        
        # 处理横盘确认的低点
        for valley_info in consolidation_valleys:
            # 使用原始波谷信息，而不是横盘期间的最低点
            valley = valley_info['valley']
            price_key = f"{valley['price']:.3f}"  # 提高精度到3位小数
            

            
            if price_key not in merged_lows:
                merged_lows[price_key] = {
                    'date': valley['date'],
                    'price': round(valley['price'], 2),
                    'drop_rate': round(valley['drop_rate'], 2),
                    'left_peak': round(valley['left_peak'], 2),
                    'left_peak_date': valley['left_peak_date'],
                    'conclusion_from': [],
                    'record': valley['record']
                }
            merged_lows[price_key]['conclusion_from'].append('flaturation')
        
        # 处理价格区间支撑位（波谷和顶点共同触及）
        for group in price_level_support:
            # 从每组中找出平均价格作为代表
            avg_price = group['price_range']['avg']
            price_key = f"{avg_price:.3f}"  # 提高精度到3位小数
            

            
            if price_key not in merged_lows:
                merged_lows[price_key] = {
                    'date': group['date_range']['earliest'],
                    'price': round(avg_price, 2),
                    'drop_rate': 0,  # 价格区间支撑位可能没有明显的跌幅
                    'left_peak': 0,
                    'left_peak_date': '',
                    'conclusion_from': [],
                    'record': {'date': group['date_range']['earliest'], 'close': avg_price}
                }
            merged_lows[price_key]['conclusion_from'].append('price_level_support')
        
        # 转换为列表
        result = list(merged_lows.values())
        
        # 过滤掉2元以下的低点（退市警戒线）
        result = [low for low in result if low['price'] >= 2.0]
        
        # 计算每个低点的重要性评分
        for low_point in result:
            # 基础分数：来源数量
            base_score = len(low_point['conclusion_from'])
            
            # 额外分数：跌幅越大，分数越高
            drop_bonus = min(low_point.get('drop_rate', 0) * 10, 5)  # 最大5分
            
            # 最终重要性评分
            low_point['importance_score'] = base_score + drop_bonus
            

        
        # 按重要性评分排序
        result.sort(key=lambda x: x['importance_score'], reverse=True)
        
        # 只保留前10个最重要的支撑位
        top_support_levels = result[:10]
        
        merged_result = []
        
        for low_point in sorted(top_support_levels, key=lambda x: x['price']):
            price = float(low_point['price'])  # 转换为float类型
            merged = False
            
            # 检查是否与已有结果合并
            for existing in merged_result:
                # 动态价格差阈值：更严格的合并，直接舍去接近的高点
                if price <= 5.0:
                    threshold = price * 0.04  # 5元以下用4%阈值（更严格）
                elif price <= 20.0:
                    threshold = price * 0.025  # 5-20元用2.5%阈值（更严格）
                elif price <= 50.0:
                    threshold = price * 0.02   # 20-50元用2%阈值（更严格）
                else:
                    threshold = price * 0.015  # 50元以上用1.5%阈值（更严格）
                
                if abs(price - float(existing['price'])) <= threshold:
                    # 合并到现有结果
                    existing['conclusion_from'].extend(low_point['conclusion_from'])
                    existing['conclusion_from'] = list(set(existing['conclusion_from']))  # 去重
                    existing['drop_rate'] = max(existing.get('drop_rate', 0), low_point.get('drop_rate', 0))
                    # 保持重要性评分
                    existing['importance_score'] = max(existing.get('importance_score', 0), low_point.get('importance_score', 0))
                    merged = True

                    break
            
            if not merged:
                # 创建新的合并结果
                merged_result.append({
                    'date': low_point['date'],
                    'price': low_point['price'],
                    'conclusion_from': low_point['conclusion_from'].copy(),
                    'drop_rate': low_point.get('drop_rate', 0),
                    'left_peak': low_point.get('left_peak', 0),
                    'left_peak_date': low_point.get('left_peak_date', ''),
                    'record': low_point.get('record', {}),
                    'importance_score': low_point.get('importance_score', 0)  # 保持重要性评分
                })
        

        
        # 为每个支撑位计算价格区间
        for low_point in merged_result:
            price = float(low_point['price'])  # 转换为float类型
            # 根据价格区间设置更合理的百分比范围
            if price <= 5.0:
                range_percent = 0.05   # 5元以下用5%范围（扩大）
            elif price <= 20.0:
                range_percent = 0.04   # 5-20元用4%范围（扩大）
            elif price <= 50.0:
                range_percent = 0.03   # 20-50元用3%范围（扩大）
            else:
                range_percent = 0.025  # 50元以上用2.5%范围（扩大）
            
            low_point['price_range'] = {
                'min': round(price * (1 - range_percent), 2),
                'max': round(price * (1 + range_percent), 2),
                'percent': range_percent * 100
            }
            low_point['display_name'] = f"{price:.2f} ({low_point['price_range']['min']:.2f}-{low_point['price_range']['max']:.2f})"
        
        # 按重要度排序（优化后的算法）
        def calculate_importance_score(low_point):
            score = 0
            
            # 1. 触及次数加分（权重最高）
            confirmation_count = len(low_point['conclusion_from'])
            score += confirmation_count * 1000  # 大幅提高触及次数的权重
            
            # 2. 重要支撑位额外加分（肉眼明显的支撑位）
            price = low_point['price']
            if (6.3 <= price <= 6.4) or (12.4 <= price <= 12.9) or (15.0 <= price <= 15.95) or (20.4 <= price <= 21.0):
                score += 1000  # 重要支撑位额外加分，大幅提升排名
            
            # 3. 跌幅加分（跌幅越大越重要）
            if 'drop_rate' in low_point and low_point['drop_rate'] > 0:
                score += low_point['drop_rate'] * 100
            
            # 4. 价格区间加分（中等价格区间更重要，避免极端低价）
            if 5.0 <= price <= 50.0:  # 中等价格区间
                score += 50
            elif 2.0 <= price < 5.0:  # 低价区间
                score += 30
            elif 50.0 < price <= 100.0:  # 高价区间
                score += 40
            
            # 5. 特定方法加分
            if 'deepest_valley' in low_point['conclusion_from']:
                score += 100  # 最深波谷额外加分
            if 'multiple_touches' in low_point['conclusion_from']:
                score += 80   # 高频触及额外加分
            if 'flaturation' in low_point['conclusion_from']:
                score += 60   # 横盘确认额外加分
            if 'price_level_support' in low_point['conclusion_from']:
                score += 90   # 价格区间支撑位额外加分（波谷和顶点共同触及）
            
            # 6. 投资实用性加分（考虑操作空间）
            # 检查该支撑位与其他支撑位的距离，距离越远操作空间越大
            price = low_point['price']
            min_distance = float('inf')
            for other_point in result:
                if other_point != low_point:
                    distance = abs(price - other_point['price'])
                    if distance < min_distance:
                        min_distance = distance
            
            if min_distance != float('inf'):
                if min_distance >= 1.0:  # 距离1元以上，操作空间充足
                    score += 100
                elif min_distance >= 0.5:  # 距离0.5-1元，操作空间适中
                    score += 50
                elif min_distance >= 0.3:  # 距离0.3-0.5元，操作空间较小
                    score += 20
            
            return score
        
        # 按重要度分数排序
        merged_result.sort(key=calculate_importance_score, reverse=True)
        
        # 更新result变量
        result = merged_result
        

        
        def calculate_importance_score(low_point):
            score = 0
            confirmation_count = len(low_point['conclusion_from'])
            score += confirmation_count * 1000  # 大幅提高触及次数的权重
            if 'drop_rate' in low_point and low_point['drop_rate'] > 0:
                score += low_point['drop_rate'] * 100
            price = low_point['price']
            if 5.0 <= price <= 50.0:
                score += 50
            elif 2.0 <= price < 5.0:
                score += 30
            elif 50.0 < price <= 100.0:
                score += 40
            if 'deepest_valley' in low_point['conclusion_from']:
                score += 100
            if 'multiple_touches' in low_point['conclusion_from']:
                score += 80
            if 'flaturation' in low_point['conclusion_from']:
                score += 60
            return score
        
        return result

    def get_historic_low_summary(self, daily_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        获取历史低点的综合摘要信息
        
        Args:
            daily_data: 日线数据列表
            
        Returns:
            Dict: 包含各种波谷检测结果的摘要
        """
        merged_lows = self.find_merged_historic_lows(daily_data)
        
        # 统计各种来源的波谷数量
        source_stats = {
            'basic_valley': 0,
            'deepest_valley': 0,
            'frequently_touched': 0,
            'consolidation': 0
        }
        
        for low_point in merged_lows:
            for source in low_point['sources']:
                method = source['method']
                if method in source_stats:
                    source_stats[method] += 1
        
        # 按可靠度分组
        high_reliability = [p for p in merged_lows if p['reliability_score'] >= 3]
        medium_reliability = [p for p in merged_lows if 1.5 <= p['reliability_score'] < 3]
        low_reliability = [p for p in merged_lows if p['reliability_score'] < 1.5]
        
        return {
            'total_low_points': len(merged_lows),
            'source_statistics': source_stats,
            'reliability_distribution': {
                'high': len(high_reliability),
                'medium': len(medium_reliability),
                'low': len(low_reliability)
            },
            'top_low_points': merged_lows[:10],  # 前10个最可靠的低点
            'all_low_points': merged_lows
        }