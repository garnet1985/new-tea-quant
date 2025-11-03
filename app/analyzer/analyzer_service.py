from datetime import datetime
from enum import Enum
import math
import random
from typing import Any, Dict, List
from loguru import logger
from .analyzer_settings import conf



class AnalyzerService:
    def __init__(self):
        pass

    @staticmethod
    def to_ratio(numerator: float, denominator: float, decimals: int = 2) -> float:
        """
        计算比率并按指定小数位四舍五入。只在分母为0时返回0.0；允许负值。
        """
        try:
            if denominator == 0:
                return 0.0
            value = float(numerator) / float(denominator)
            return round(value, decimals)
        except ZeroDivisionError:
            return 0.0
        except Exception:
            return 0.0

    @staticmethod
    def to_percent(numerator: float, denominator: float, decimals: int = 2) -> float:
        """
        与 to_ratio 相同的入参，输出为百分比（ratio*100）。仅分母为0时返回0.0，允许负值。
        """
        try:
            if denominator == 0:
                return 0.0
            value = float(numerator) / float(denominator)
            return round(value * 100.0, decimals)
        except ZeroDivisionError:
            return 0.0
        except Exception:
            return 0.0

    @staticmethod
    def get_duration_in_days(start_date: str, end_date: str) -> int:
        start = datetime.strptime(start_date, '%Y%m%d')
        end = datetime.strptime(end_date, '%Y%m%d')
        return (end - start).days
    
    @staticmethod
    def get_annual_return(profit_rate: float, duration_in_days: int, is_trading_days: bool = False) -> float:
        """
        计算年化收益率（使用复利公式）
        
        Args:
            profit_rate: 总收益率（小数形式，如0.1表示10%）
            duration_in_days: 投资持续天数
            is_trading_days: 是否使用交易日计算
            
        Returns:
            float: 年化收益率（百分比形式）
        """
    
        if is_trading_days:
            years = duration_in_days / 250.0
        else:
            years = duration_in_days / 365.0

        if duration_in_days <= 0 or profit_rate == 0:
            return 0.0
        
        if years <= 0:
            return 0.0
        
        # 使用复利公式：年化收益率 = ((1 + 总收益率) ^ (1/年数)) - 1
        annual_return = ((1 + profit_rate) ** (1 / years)) - 1
        return annual_return

    @staticmethod
    def parse_yyyymmdd(date_str: str):
        """
        安全解析 YYYYMMDD，失败返回 None。
        """
        if not date_str:
            return None
        try:
            return datetime.strptime(str(date_str), '%Y%m%d')
        except Exception:
            return None

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
    def get_mean(values: List[float]) -> float:
        """
        获得数值的平均值
        
        Args:
            values: 数值列表
            
        Returns:
            float: 平均值
        """
        if not values:
            return 0.0
        return sum(values) / len(values)
    
    @staticmethod
    def get_median(values: List[float]) -> float:
        """
        获得数值的中位数
        
        Args:
            values: 数值列表
            
        Returns:
            float: 中位数
        """
        if not values:
            return 0.0
        sorted_values = sorted(values)
        n = len(sorted_values)
        # 如果是偶数个，取中间两个的平均值
        if n % 2 == 0:
            return (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2.0
        else:
            return sorted_values[n // 2]

    @staticmethod
    def get_standard_deviation(values: List[float]) -> float:
        """
        获得数值的标准差
        
        Args:
            values: 数值列表
            
        Returns:
            float: 标准差
        """
        if not values:
            return 0.0
        
        mean = AnalyzerService.get_mean(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        
        return math.sqrt(variance)

    @staticmethod
    def get_slope(values: List[float]) -> float:
        """
        获得数值的趋势斜率（使用线性回归）
        
        Args:
            values: 数值列表（按时间顺序排列）
            
        Returns:
            float: 斜率（表示每个时间单位的变化量）
        """
        if not values or len(values) < 2:
            return 0.0
        
        n = len(values)
        # x轴为索引序列：0, 1, 2, ..., n-1
        x_sum = sum(range(n))
        y_sum = sum(values)
        xy_sum = sum(i * values[i] for i in range(n))
        x2_sum = sum(i * i for i in range(n))
        
        # 线性回归斜率公式: slope = (n*Σxy - Σx*Σy) / (n*Σx² - (Σx)²)
        denominator = n * x2_sum - x_sum * x_sum
        if denominator == 0:
            return 0.0
        
        slope = (n * xy_sum - x_sum * y_sum) / denominator
        
        return slope










    # =======================    Utils    =================================

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

    # ========================================================
    # 股票列表采样方法
    # ========================================================
    
    @staticmethod
    def sample_stock_list(stock_list: List[Dict[str, Any]], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        根据settings配置采样股票列表
        
        Args:
            stock_list: 原始股票列表
            settings: 策略设置
            
        Returns:
            采样后的股票列表
        """
        try:
            # 获取simulation配置
            # 注意：sampling_amount 已经由 validator 验证过了，这里不会有 None 的情况
            simulation_config = settings.get('simulation', {})
            sampling_config = simulation_config.get('sampling', {})
            sampling_strategy = sampling_config.get('strategy', 'uniform')
            sampling_amount = simulation_config.get('sampling_amount', 5)  # 默认为5（采样5只股票）
            
            if sampling_amount > 0:
                # 根据采样策略执行相应的采样方法
                if sampling_strategy == 'uniform':
                    result = AnalyzerService._uniform_sampling(stock_list, sampling_amount)
                    logger.info(f"📊 均匀间隔采样: {len(result)} 只股票")

                elif sampling_strategy == 'stratified':
                    stratified_config = sampling_config.get('stratified', {})
                    seed = stratified_config.get('seed', 42)
                    result = AnalyzerService._stratified_sampling(stock_list, sampling_amount, seed)
                    logger.info(f"📊 分层采样: {len(result)} 只股票 (seed={seed})")

                elif sampling_strategy == 'random':
                    random_config = sampling_config.get('random', {})
                    seed = random_config.get('seed', 42)
                    result = AnalyzerService._random_sampling(stock_list, sampling_amount, seed)
                    logger.info(f"📊 随机采样: {len(result)} 只股票 (seed={seed})")

                elif sampling_strategy == 'pool':
                    pool_config = sampling_config.get('pool', {})
                    stock_pool = pool_config.get('stock_pool', [])
                    if stock_pool:
                        result = AnalyzerService._filter_list_by_ids(stock_list, stock_pool)
                        if len(result) > sampling_amount:
                            result = result[:sampling_amount]
                        logger.info(f"🎯 股票池采样: {len(result)} 只股票")
                    else:
                        logger.warning("⚠️ 启用了股票池采样但股票池为空，将使用全量模式")
                        result = stock_list
                        logger.info(f"🌐 使用全量模式，扫描 {len(result)} 只股票")

                elif sampling_strategy == 'blacklist':
                    blacklist_config = sampling_config.get('blacklist', {})
                    blacklist = blacklist_config.get('blacklist', [])
                    if blacklist:
                        result = AnalyzerService._filter_list_by_ids(stock_list, blacklist)
                        if len(result) > sampling_amount:
                            result = result[:sampling_amount]
                        logger.info(f"📋 黑名单采样: {len(result)} 只股票")
                    else:
                        logger.warning("⚠️ 启用了黑名单采样但黑名单为空，将使用全量模式")
                        result = stock_list
                        logger.info(f"🌐 使用全量模式，扫描 {len(result)} 只股票")

                else:  # continuous
                    continuous_config = sampling_config.get('continuous', {})
                    start_idx = continuous_config.get('start_idx', 0)
                    result = stock_list[start_idx:start_idx + sampling_amount]
                    logger.info(f"🔢 连续采样: {len(result)} 只股票 (从索引 {start_idx} 开始)")

                return result

            else:
                logger.info(f"🌐 使用全量模式，扫描 {len(stock_list)} 只股票")
                return stock_list

        except Exception as e:
            logger.error(f"❌ 股票列表采样失败: {e}")
            return stock_list

    @staticmethod
    def _filter_list_by_ids(stock_list: List[Dict[str, Any]], stock_ids: List[str]) -> List[Dict[str, Any]]:
        """根据股票ID列表过滤股票"""
        new_list = []
        for stock in stock_list:
            if stock.get('id') in stock_ids:
                new_list.append(stock)
        return new_list
    
    @staticmethod
    def _uniform_sampling(stock_list: List[Dict[str, Any]], sample_size: int) -> List[Dict[str, Any]]:
        """
        均匀间隔采样 - 保证样本分布均匀，结果可重现
        """
        total_stocks = len(stock_list)
        
        if sample_size >= total_stocks:
            return stock_list
        
        # 计算采样间隔
        step = total_stocks / sample_size
        
        # 生成均匀分布的索引
        indices = []
        for i in range(sample_size):
            # 使用固定偏移避免总是从0开始
            offset = i * step
            index = int(offset + (step * 0.5))  # 取间隔中点
            indices.append(index)
        
        # 提取采样股票
        sampled_stocks = [stock_list[idx] for idx in indices if idx < total_stocks]
        
        return sampled_stocks
    
    @staticmethod
    def _stratified_sampling(stock_list: List[Dict[str, Any]], sample_size: int, seed: int = 42) -> List[Dict[str, Any]]:
        """
        分层采样 - 按股票代码前缀分层，确保不同市场都有代表
        """
        # 按股票代码前缀分组
        groups = {}
        for stock in stock_list:
            stock_id = stock['id']
            prefix = stock_id[:2]  # 取前两位作为分组依据
            
            if prefix not in groups:
                groups[prefix] = []
            groups[prefix].append(stock)
        
        # 按组大小分配采样数量
        sampled_stocks = []
        random.seed(seed)
        
        for prefix, stocks in groups.items():
            # 按比例分配采样数量
            group_sample_size = max(1, int(sample_size * len(stocks) / len(stock_list)))
            
            # 从该组中随机采样
            if group_sample_size >= len(stocks):
                sampled_stocks.extend(stocks)
            else:
                sampled_stocks.extend(random.sample(stocks, group_sample_size))
        
        # 如果采样数量不足，从剩余股票中补充
        if len(sampled_stocks) < sample_size:
            remaining_stocks = [s for s in stock_list if s not in sampled_stocks]
            additional_needed = sample_size - len(sampled_stocks)
            if additional_needed <= len(remaining_stocks):
                sampled_stocks.extend(random.sample(remaining_stocks, additional_needed))
        
        return sampled_stocks
    
    @staticmethod
    def _random_sampling(stock_list: List[Dict[str, Any]], sample_size: int, seed: int = 42) -> List[Dict[str, Any]]:
        """
        随机采样 - 完全随机，但使用固定种子保证可重现
        """
        if seed is not None:
            random.seed(seed)
        
        if sample_size >= len(stock_list):
            return stock_list
        
        return random.sample(stock_list, sample_size)


    