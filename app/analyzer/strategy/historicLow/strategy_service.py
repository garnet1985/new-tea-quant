import pprint
import math
from typing import Dict, List, Any, Tuple
from typing_extensions import Optional

from loguru import logger
from .strategy_settings import strategy_settings
from app.analyzer.analyzer_service import AnalyzerService
from datetime import datetime
from .strategy_entity import StrategyEntity


class HistoricLowService:
    """HistoricLow策略的静态服务类"""
    
    @staticmethod
    def validate_strategy_settings(settings: dict) -> tuple[bool, list[str]]:
        """
        验证策略设置的基本常识错误
        
        Returns:
            tuple: (是否有效, 错误信息列表)
        """
        errors = []
        
        # 检查基本结构
        if 'goal' not in settings:
            errors.append("缺少goal配置")
            return False, errors
        
        goal = settings['goal']
        
        # 检查止盈配置 - 主要检查总平仓比例不超过100%
        if 'take_profit' in goal and 'stages' in goal['take_profit']:
            total_sell_ratio = 0
            for stage in goal['take_profit']['stages']:
                sell_ratio = stage.get('sell_ratio', 0)
                total_sell_ratio += sell_ratio
            
            if total_sell_ratio > 1:
                errors.append(f"总平仓比例({total_sell_ratio:.1%})超过100%")
        
        # 检查止损配置 - 检查动态止损比例是否合理
        if 'stop_loss' in goal and 'stages' in goal['stop_loss']:
            for stage in goal['stop_loss']['stages']:
                if stage.get('name') == 'dynamic':
                    ratio = abs(float(stage.get('ratio', 0)))
                    if ratio > 0.5:  # 动态止损比例不应超过50%
                        errors.append(f"动态止损比例({ratio:.1%})过高")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def calculate_freeze_data_stats(freeze_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算freeze data期间的涨跌幅统计信息
        
        Args:
            freeze_data: 冻结期数据
            
        Returns:
            Dict[str, Any]: 包含平均涨跌幅和标准差的统计信息
        """
        if not freeze_data:
            return {
                'mean_change_rate': 0.0,
                'std_change_rate': 0.0,
                'positive_days': 0,
                'negative_days': 0,
                'total_days': 0,
                'max_close': 0.0,
                'min_close': 0.0,
                'close_range': 0.0,
                'close_ratio': 0.0,
                'range_to_invest_ratio': 0.0
            }
        
        # 提取涨跌幅数据
        change_rates = []
        positive_days = 0
        negative_days = 0
        
        # 记录收盘价的最大值和最小值
        max_close = 0.0
        min_close = float('inf')
        max_close_date = ''
        min_close_date = ''
        
        for record in freeze_data:
            if 'priceChangeRateDelta' in record and record['priceChangeRateDelta'] is not None:
                change_rate = float(record['priceChangeRateDelta']) / 100.0  # 转换为小数形式
                change_rates.append(change_rate)
                
                if change_rate > 0:
                    positive_days += 1
                elif change_rate < 0:
                    negative_days += 1
            
            # 记录收盘价的最大值和最小值
            close_price = float(record['close'])
            if close_price > max_close:
                max_close = close_price
                max_close_date = record['date']
            if close_price < min_close:
                min_close = close_price
                min_close_date = record['date']
        
        if not change_rates:
            return {
                'mean_change_rate': 0.0,
                'std_change_rate': 0.0,
                'positive_days': 0,
                'negative_days': 0,
                'total_days': len(freeze_data),
                'max_close': max_close,
                'min_close': min_close,
                'close_range': max_close - min_close,
                'close_ratio': max_close / min_close if min_close > 0 else 0.0,
                'range_to_invest_ratio': 0.0
            }
        
        # 计算统计信息
        import statistics
        mean_change_rate = statistics.mean(change_rates)
        std_change_rate = statistics.stdev(change_rates) if len(change_rates) > 1 else 0.0
        
        # 计算收盘价相关指标
        close_range = max_close - min_close
        close_ratio = max_close / min_close if min_close > 0 else 0.0
        
        # 投资时的价格（freeze data的最后一天）
        invest_close = float(freeze_data[-1]['close'])
        range_to_invest_ratio = close_range / invest_close if invest_close > 0 else 0.0
        
        return {
            'mean_change_rate': round(mean_change_rate, 4),
            'std_change_rate': round(std_change_rate, 4),
            'positive_days': positive_days,
            'negative_days': negative_days,
            'total_days': len(freeze_data),
            'max_close': round(max_close, 4),
            'min_close': round(min_close, 4),
            'max_close_date': max_close_date,
            'min_close_date': min_close_date,
            'close_range': round(close_range, 4),
            'close_ratio': round(close_ratio, 4),
            'range_to_invest_ratio': round(range_to_invest_ratio, 4)
        }
    
    @staticmethod
    def find_historic_low_points(daily_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        使用改进算法：从当前数据倒推指定年份，取到它们的最低点
        增加敏感度，更早发现投资机会
        """
        if not daily_records or len(daily_records) < 2000:  # 至少需要足够的历史数据
            return []
        
        low_points = []
        current_date = daily_records[-1]['date']
        
        # 从settings获取回溯年份，过滤掉0
        years_to_lookback = [year for year in strategy_settings['daily_data_requirements']['low_points_ref_years']]
        
        for years in years_to_lookback:
            # 计算目标日期（years年前）
            target_year = int(current_date[:4]) - years
            target_date = f"{target_year}{current_date[4:]}"
            
            # 找到目标日期附近的数据
            target_records = []
            for record in daily_records:
                if record['date'][:4] == str(target_year):
                    target_records.append(record)
            
            if not target_records:
                continue
            
            # 找到该年的最低点
            min_record = min(target_records, key=lambda x: float(x['close']))
            min_price = float(min_record['close'])
            min_date = min_record['date']
            
            # 使用新的投资范围设置（上方10%，下方5%）
            upper_ratio, lower_ratio = HistoricLowService.calculate_dynamic_price_range(min_price)
            range_min = min_price * (1 - lower_ratio)  # 下方5%
            range_max = min_price * (1 + upper_ratio)  # 上方10%
            
            low_points.append({
                'min': range_min,
                'max': range_max,
                'avg': min_price,
                'term': years,
                'valley_type': f'{years}year_low',
                'target_year': target_year,
                'lowest_price': min_price,
                'lowest_date': min_date
            })
        
        return low_points


    @staticmethod
    def is_meet_strategy_requirements(daily_data: List[Dict[str, Any]]) -> bool:
        min_required = strategy_settings.get('daily_data_requirements', {}).get('min_required_daily_records', 2000)
        return len(daily_data) >= min_required

    
    @staticmethod
    def calculate_dynamic_price_range(low_point_price: float) -> Tuple[float, float]:
        """
        计算动态价格区间比例（支持上下限不同）
        
        Args:
            low_point_price: 历史低点价格
            
        Returns:
            Tuple[float, float]: (上方比例, 下方比例)
        """
        # 从settings获取配置
        low_point_config = strategy_settings.get('low_point_invest_range', {})
        upper_bound_ratio = low_point_config.get('upper_bound', 0.1)  # 上方10%
        lower_bound_ratio = low_point_config.get('lower_bound', 0.05)  # 下方5%
        min_range = low_point_config.get('min', 0.2)
        max_range = low_point_config.get('max', 10.0)
        
        # 计算上方和下方的绝对区间
        upper_absolute_range = low_point_price * upper_bound_ratio
        lower_absolute_range = low_point_price * lower_bound_ratio
        
        # 应用最小/最大区间限制
        upper_absolute_range = max(min(upper_absolute_range, max_range), min_range)
        lower_absolute_range = max(min(lower_absolute_range, max_range), min_range)
        
        # 计算对应的比例
        upper_ratio = upper_absolute_range / low_point_price
        lower_ratio = lower_absolute_range / low_point_price
        
        return upper_ratio, lower_ratio
    
    @staticmethod
    def is_in_invest_range(record, low_point, freeze_data=None):
        """
        检查是否在投资范围内
        新增条件：在freeze data内没有出现比历史低点更低的价格
        新增条件：检查冻结期内是否已经触及过相同的投资点
        """
        if low_point is None:
            return False
        
        current_price = float(record['close'])
        low_point_price = float(low_point['min'])  # 历史低点价格
        
        # 计算动态价格区间（支持上下限不同）
        upper_ratio, lower_ratio = HistoricLowService.calculate_dynamic_price_range(low_point_price)
        lower_bound = low_point_price * (1 - lower_ratio)  # 下方5%
        upper_bound = low_point_price * (1 + upper_ratio)  # 上方10%
        
        # 基本条件：当前价格在动态价格区间内
        basic_condition = current_price >= lower_bound and current_price <= upper_bound
        
        if not basic_condition:
            return False
        
        # 新增条件：检查freeze data内的情况
        if freeze_data:
            freeze_min_price = min(float(r['close']) for r in freeze_data)
            
            # 条件1：如果freeze data的最低点比当前价格还低，说明在冻结期内已经出现过更低的价格，不投资
            if freeze_min_price < current_price:
                return False
            
            # 条件2：当前价格不应该比freeze data的最低点高出太多（超过5%）
            if current_price > freeze_min_price * 1.05:
                return False
            
            # 条件3：检查是否为最佳投资时机（避免多次触底后的投资）
            if not HistoricLowService.is_optimal_investment_timing(current_price, low_point, freeze_data):
                return False
            
        
        return True

    @staticmethod
    def is_amplitude_sufficient(freeze_data: List[Dict[str, Any]]) -> bool:
        """
        检查冻结期数据的振幅是否足够
        过滤掉振幅小于阈值的投资
        
        Args:
            freeze_data: 冻结期数据
            
        Returns:
            bool: 振幅是否足够
        """
        # 从策略设置中获取振幅过滤配置
        from .strategy_settings import strategy_settings
        
        amplitude_config = strategy_settings.get('amplitude_filter', {})
        if not amplitude_config:
            return True  # 如果没有配置振幅过滤，直接返回True
        
        min_amplitude = amplitude_config.get('min_amplitude', 0.10)
        if not freeze_data or len(freeze_data) < 2:
            return False
        
        # 计算冻结期内的价格变化百分比
        prices = [float(r['close']) for r in freeze_data]
        day_changes_pct = []
        
        for i in range(1, len(prices)):
            prev_price = prices[i-1]
            curr_price = prices[i]
            change_pct = (curr_price - prev_price) / prev_price
            day_changes_pct.append(change_pct)
        
        if not day_changes_pct:
            return False
        
        # 计算振幅（最大值 - 最小值）
        amplitude = max(day_changes_pct) - min(day_changes_pct)
        
        # 检查振幅是否达到最小阈值
        return amplitude >= min_amplitude

    @staticmethod
    def is_optimal_investment_timing(current_price: float, low_point: Dict[str, Any], freeze_data: List[Dict[str, Any]]) -> bool:
        """
        判断是否为最佳投资时机
        优先选择第一次触底的机会，避免多次触底后的投资
        
        Args:
            current_price: 当前价格
            low_point: 历史低点信息
            freeze_data: 冻结期数据
            
        Returns:
            bool: 是否为最佳投资时机
        """
        if not freeze_data or len(freeze_data) < 2:
            return True  # 没有冻结期数据，认为是第一次机会
        
        # 计算触底次数
        touch_count = HistoricLowService._count_touch_times_in_freeze(current_price, low_point, freeze_data)
        
        # 获取最大触底次数限制
        max_touch_times = strategy_settings.get('low_point_invest_range', {}).get('max_touch_times', 2)
        
        # 如果触底次数小于最大限制，可以投资
        return touch_count < max_touch_times

    @staticmethod
    def _count_touch_times_in_freeze(current_price: float, low_point: Dict[str, Any], freeze_data: List[Dict[str, Any]]) -> int:
        """
        计算冻结期内触及投资点的次数
        
        Args:
            current_price: 当前价格
            low_point: 历史低点信息
            freeze_data: 冻结期数据
            
        Returns:
            int: 触及投资点的次数
        """
        if not freeze_data or len(freeze_data) < 2:
            return 0
        
        low_point_price = float(low_point['min'])
        
        # 计算投资价格区间（支持上下限不同）
        upper_ratio, lower_ratio = HistoricLowService.calculate_dynamic_price_range(low_point_price)
        lower_bound = low_point_price * (1 - lower_ratio)  # 下方5%
        upper_bound = low_point_price * (1 + upper_ratio)  # 上方10%
        
        # 统计冻结期内触及投资点的次数
        touch_count = 0
        
        for record in freeze_data[:-1]:  # 排除最后一天（当前天）
            record_price = float(record['close'])
            
            # 检查是否在投资范围内
            if lower_bound <= record_price <= upper_bound:
                touch_count += 1
        
        return touch_count

    @staticmethod
    def _is_investment_point_already_touched_in_freeze(current_price: float, low_point: Dict[str, Any], freeze_data: List[Dict[str, Any]]) -> bool:
        """
        检查冻结期内是否已经触及过相同的投资点
        
        Args:
            current_price: 当前价格
            low_point: 历史低点信息
            freeze_data: 冻结期数据
            
        Returns:
            bool: True表示该投资点已经在冻结期内触及过，False表示未触及过
        """
        # 获取最大触底次数限制
        max_touch_times = strategy_settings.get('low_point_invest_range', {}).get('max_touch_times', 2)
        
        # 计算触底次数
        touch_count = HistoricLowService._count_touch_times_in_freeze(current_price, low_point, freeze_data)
        
        # 如果触及次数超过限制，说明不应该再投资
        return touch_count >= max_touch_times

    @staticmethod
    def is_slope_too_steep(klines: List[Dict[str, Any]]) -> bool:
        """
        检查近期股价斜率是否过于陡峭下跌
        
        Args:
            klines: 股价数据列表
            
        Returns:
            bool: True表示斜率过于陡峭，False表示正常
        """
        # 使用最后10个元素进行斜率检查
        days = 10
        max_slope = -20.0  # 调整为-30度，过滤33%以上下跌
        
        if len(klines) < days:
            return False  # 数据不足，不检查
        
        # 取最近days天的数据
        recent_data = klines[-days:]
        
        # 计算斜率（使用线性回归）
        prices = [float(r['close']) for r in recent_data]
        dates = [i for i in range(len(recent_data))]  # 使用索引作为x轴
        
        # 计算线性回归斜率
        n = len(prices)
        sum_x = sum(dates)
        sum_y = sum(prices)
        sum_xy = sum(x * y for x, y in zip(dates, prices))
        sum_x2 = sum(x * x for x in dates)
        
        # 斜率公式: slope = (n*sum_xy - sum_x*sum_y) / (n*sum_x2 - sum_x^2)
        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            return False  # 避免除零错误
        
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        
        # 将斜率转换为角度（度）
        # 使用价格变化率来计算角度
        if len(prices) > 1:
            price_change_ratio = (prices[-1] - prices[0]) / prices[0]
            # 使用更直观的角度计算方式
            # 将价格变化率映射到-90到90度的范围
            # 例如：-50%变化率对应-45度，-100%变化率对应-90度
            if price_change_ratio <= -1.0:
                angle_degrees = -90.0  # 完全归零
            else:
                # 使用线性映射：-50% -> -45度，-100% -> -90度
                angle_degrees = price_change_ratio * 90.0
        else:
            angle_degrees = 0
        
        # 检查是否过于陡峭下跌
        is_too_steep = angle_degrees < max_slope
        
        if is_too_steep:
            logger.debug(f"股价斜率过于陡峭: {angle_degrees:.2f}度 (限制: {max_slope}度)")
        
        return is_too_steep

    @staticmethod
    def is_in_continuous_limit_down(klines: List[Dict[str, Any]]) -> bool:
        """
        检查当前是否处于连续跌停中
        
        Args:
            klines: k线记录
            
        Returns:
            bool: True表示在连续跌停中，False表示不在连续跌停中
        """
        if not klines or len(klines) < 2:
            return False
        
        # 检查最近3天，专注于连续跌停识别
        recent_klines = klines[-3:] if len(klines) >= 3 else klines
        
        # 1. 检查投资前一天是否跌停（跌幅超过9%）
        if len(recent_klines) >= 2:
            prev_close = float(recent_klines[-2]['close'])
            curr_close = float(recent_klines[-1]['close'])
            prev_day_drop_rate = (prev_close - curr_close) / prev_close
            
            # 投资前一天跌停（跌幅超过9%），需要过滤
            if prev_day_drop_rate > 0.09:
                return True
        
        # 2. 检查是否有连续跌停（连续2天以上跌幅接近10%）
        consecutive_limit_down = 0
        max_consecutive = 0
        
        for i in range(1, len(recent_klines)):
            prev_close = float(recent_klines[i-1]['close'])
            curr_close = float(recent_klines[i]['close'])
            daily_drop_rate = (prev_close - curr_close) / prev_close
            
            # 跌停判断：跌幅接近10%（考虑ST股票5%跌停）
            if daily_drop_rate > 0.095:  # 9.5%以上认为是跌停
                consecutive_limit_down += 1
                max_consecutive = max(max_consecutive, consecutive_limit_down)
            else:
                consecutive_limit_down = 0
        
        # 连续2天以上跌停认为是连续跌停
        has_consecutive_limit_down = max_consecutive >= 2
        
        # 3. 检查是否有跌停且振幅接近0（典型的跌停特征）
        has_limit_down_with_zero_amplitude = False
        for kline in recent_klines:
            high = float(kline.get('highest', kline['close']))
            low = float(kline.get('lowest', kline['close']))
            close = float(kline['close'])
            amplitude = (high - low) / close if close > 0 else 0
            
            # 振幅小于0.5%且价格下跌，认为是跌停
            if amplitude < 0.005:  # 振幅小于0.5%
                has_limit_down_with_zero_amplitude = True
                break
        
        # 4. 检查是否有跌停且成交量异常低（跌停特征）
        has_limit_down_with_low_volume = False
        if len(recent_klines) >= 2:
            for i in range(1, len(recent_klines)):
                prev_close = float(recent_klines[i-1]['close'])
                curr_close = float(recent_klines[i]['close'])
                daily_drop_rate = (prev_close - curr_close) / prev_close
                
                if daily_drop_rate > 0.095:  # 跌停
                    volume = float(recent_klines[i].get('volume', 0))
                    # 跌停且成交量异常低（小于500手）
                    if volume < 500:
                        has_limit_down_with_low_volume = True
                        break
        
        # 综合判断：投资前一天跌停 或 连续跌停 或 跌停+零振幅 或 跌停+低成交量
        return (has_consecutive_limit_down or has_limit_down_with_zero_amplitude or 
                has_limit_down_with_low_volume)
    
    
    @staticmethod
    def filter_out_negative_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # 取连续片段（最后一个负值之后）
        if not records:
            return []

        last_negative_idx = -1
        for idx, rec in enumerate(records):
            try:
                close_v = float(rec.get('close', 0))
                high_v = float(rec.get('highest', close_v))
                low_v = float(rec.get('lowest', close_v))
            except Exception:
                # 非法记录按负值处理，推动起点
                last_negative_idx = idx
                continue
            if close_v < 0 or high_v < 0 or low_v < 0:
                last_negative_idx = idx

        
        continuous_slice = records[last_negative_idx + 1:] if last_negative_idx + 1 < len(records) else []
        
        return continuous_slice


    @staticmethod
    def calculate_investment_targets(record_of_today: Dict[str, Any], low_point: Dict[str, Any], freeze_data: List[Dict[str, Any]], daily_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算投资目标：止损和止盈价格
        使用新的分段平仓策略配置
        """
        current_price = float(record_of_today['close'])

        # 检查价格是否有效
        if current_price <= 0:
            return None

        if not freeze_data or not daily_records:
            return None

        min_price = min(freeze_data, key=lambda x: float(x['close']))['close']
        max_price = max(freeze_data, key=lambda x: float(x['close']))['close']

        if min_price < low_point['min']:
            return None

        # 使用新的配置结构
        goal_config = strategy_settings['goal']
        
        # 获取初始止损配置（第一个阶段）
        stop_loss_stages = goal_config['stop_loss']['stages']
        initial_stop_loss_stage = stop_loss_stages[0]  # 初始阶段
        initial_stop_loss_ratio = abs(float(initial_stop_loss_stage['ratio']))
        
        # 获取最后一个止盈阶段作为最大止盈目标
        take_profit_stages = goal_config['take_profit']['stages']
        max_take_profit_stage = take_profit_stages[-1]  # 最后一个阶段
        max_take_profit_ratio = float(max_take_profit_stage['ratio'])
        
        # 计算具体价格
        stop_loss_price = current_price * (1 - initial_stop_loss_ratio)
        take_profit_price = current_price * (1 + max_take_profit_ratio)

        
        return {
            'stop_loss_price': stop_loss_price,
            'take_profit_price': take_profit_price,
            'stop_loss_ratio': initial_stop_loss_ratio,
            'take_profit_ratio': max_take_profit_ratio
        }


    @staticmethod
    def to_opportunity(stock_info: Dict[str, Any], record_of_today: Dict[str, Any], low_point: Dict[str, Any]) -> Dict[str, Any]:
        """使用 StrategyEntity 生成机会对象"""
        return StrategyEntity.to_opportunity(stock_info, record_of_today, low_point)

    @staticmethod
    def to_investment(opportunity: Dict[str, Any], investment_targets: Dict[str, Any], freeze_data: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """使用 StrategyEntity 生成投资对象"""
        return StrategyEntity.to_investment(opportunity, investment_targets, freeze_data, calculate_freeze_stats=False)

    @staticmethod
    def to_session_summary(session_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """使用 StrategyEntity 生成会话汇总"""
        return StrategyEntity.to_session_summary(session_results)

    @staticmethod
    def to_stock_summary(stock_simulation_result: Dict[str, Any]) -> Dict[str, Any]:
        """使用 StrategyEntity 生成股票汇总"""
        return StrategyEntity.to_stock_summary(stock_simulation_result)

    @staticmethod
    def split_daily_data_for_analysis(daily_data: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        分割日线数据为冻结期和历史期
        
        Args:
            daily_data: 完整的日线数据列表
            
        Returns:
            Dict: 包含冻结期和历史期数据的分割结果
        """
        # 获取配置参数
        freeze_days = strategy_settings['daily_data_requirements']['freeze_period_days']
        
        # 分割数据
        freeze_records = daily_data[-freeze_days:]  # 最近200个交易日（冻结期）
        history_records = daily_data[:-freeze_days]  # 之前的数据（历史期）

        return freeze_records, history_records