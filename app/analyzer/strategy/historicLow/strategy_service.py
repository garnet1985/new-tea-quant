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
        使用固定年份低点算法找到历史低点
        算法：取3年、5年、8年的最低点作为参考低点
        """
        if not daily_records or len(daily_records) < 2000:  # 至少需要足够的历史数据
            return []
        
        # 获取冻结期天数
        freeze_days = strategy_settings['daily_data_requirements']['freeze_period_days']
        freeze_start_idx = max(0, len(daily_records) - freeze_days - 1)
        
        # 只分析冻结期之前的数据
        historical_records = daily_records[:freeze_start_idx]
        
        # 获取当前日期
        current_date = daily_records[-1]['date']
        current_year = int(current_date[:4])
        
        # 从设置中获取要查找的年份
        target_years = strategy_settings['daily_data_requirements']['low_points_ref_years']
        low_points = []
        
        for years_back in target_years:
            target_year = current_year - years_back
            
            # 找到该年份的最低点
            year_records = [record for record in historical_records 
                          if record['date'].startswith(str(target_year))]
            
            if not year_records:
                continue
                
            # 找到该年份的最低价格
            min_record = min(year_records, key=lambda x: float(x['close']))
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
                'term': years_back,
                'valley_type': f'{years_back}year_low',
                'target_year': target_year,
                'lowest_price': min_price,
                'lowest_date': min_date
            })
        
        return low_points

    @staticmethod
    def _find_simple_valleys(prices: List[float], dates: List[str], 
                            window: int = 20, min_rebound: float = 0.15) -> List[Dict[str, Any]]:
        """
        简单的波谷识别算法
        - window: 滑动窗口大小（20个交易日）
        - min_rebound: 最小反弹幅度（15%）
        """
        valleys = []
        
        for i in range(window, len(prices) - window):
            current_price = prices[i]
            
            # 检查是否为局部最低点
            left_min = min(prices[i-window:i])
            right_min = min(prices[i+1:i+window+1])
            
            if current_price <= left_min and current_price <= right_min:
                # 检查后续是否有显著反弹
                future_window = min(window * 2, len(prices) - i - 1)  # 看未来40天或到数据末尾
                if future_window > 0:
                    future_max = max(prices[i:i+future_window])
                    rebound_ratio = (future_max - current_price) / current_price
                    
                    if rebound_ratio >= min_rebound:
                        valleys.append({
                            'index': i,
                            'price': current_price,
                            'date': dates[i],
                            'rebound_ratio': rebound_ratio
                        })
        
        return valleys

    @staticmethod
    def _select_diverse_low_points(low_points: List[Dict[str, Any]], max_count: int) -> List[Dict[str, Any]]:
        """
        选择多样化的低点，控制时间和价格密度
        - 时间密度：不能都出自同一时间段（至少间隔1年）
        - 价格密度：不能价格太接近（至少间隔10%）
        """
        if len(low_points) <= max_count:
            return low_points
        
        selected_points = []
        
        for lp in low_points:
            if len(selected_points) >= max_count:
                break
                
            # 检查是否与已选择的点冲突
            is_conflict = False
            
            for selected in selected_points:
                # 检查时间密度（至少间隔1年）
                time_diff = abs(int(lp['target_year']) - int(selected['target_year']))
                if time_diff < 1:
                    is_conflict = True
                    break
                
                # 检查价格密度（至少间隔15%）
                if selected['lowest_price'] > 0:
                    price_diff = abs(lp['lowest_price'] - selected['lowest_price']) / selected['lowest_price']
                else:
                    price_diff = 0
                if price_diff < 0.15:  # 15%
                    is_conflict = True
                    break
            
            # 如果没有冲突，则选择这个点
            if not is_conflict:
                selected_points.append(lp)
        
        return selected_points

    @staticmethod
    def _find_significant_valleys(prices: List[float], dates: List[str], 
                                 window: int = 20, min_rebound: float = 0.15) -> List[Dict[str, Any]]:
        """
        找到有意义的低点
        基于两个关键特征：
        1. 多次测试的支撑位（多次触及后反弹）
        2. 关键转折点（历史低点后趋势反转）
        """
        valleys = []
        
        # 第一步：找到所有候选低点（局部极值）
        candidate_valleys = []
        for i in range(window, len(prices) - window):
            current_price = prices[i]
            
            # 检查是否为局部最低点
            left_min = min(prices[i-window:i])
            right_min = min(prices[i+1:i+window+1])
            
            if current_price <= left_min and current_price <= right_min:
                candidate_valleys.append({
                    'index': i,
                    'price': current_price,
                    'date': dates[i]
                })
        
        # 第二步：对每个候选低点进行质量评估
        for valley in candidate_valleys:
            quality_score = HistoricLowService._evaluate_valley_quality(
                valley, prices, dates, window
            )
            
            if quality_score['is_significant']:
                valleys.append({
                    'index': valley['index'],
                    'price': valley['price'],
                    'date': valley['date'],
                    'rebound_ratio': quality_score['rebound_ratio'],
                    'touch_count': quality_score['touch_count'],
                    'quality_score': quality_score  # 保存完整的质量评估结果
                })
        
        return valleys

    @staticmethod
    def _evaluate_valley_quality(valley: Dict[str, Any], prices: List[float], 
                                dates: List[str], window: int) -> Dict[str, Any]:
        """
        评估低点质量
        基于两个关键指标：
        1. 多次测试支撑位：计算触及后反弹的次数
        2. 关键转折点：检查是否为历史低点后趋势反转
        """
        valley_price = valley['price']
        valley_index = valley['index']
        valley_date = valley['date']
        
        # 计算触及范围（±2%）
        touch_range = 0.02
        price_min = valley_price * (1 - touch_range)
        price_max = valley_price * (1 + touch_range)
        
        # 指标1：多次测试支撑位
        touch_rebound_count = 0
        total_rebound_ratio = 0
        
        # 从低点之后开始检查
        for i in range(valley_index + 1, len(prices)):
            current_price = prices[i]
            
            # 检查是否触及低点范围
            if price_min <= current_price <= price_max:
                # 检查后续是否有反弹
                future_window = min(20, len(prices) - i - 1)
                if future_window > 0:
                    future_max = max(prices[i:i+future_window])
                    rebound_ratio = (future_max - valley_price) / valley_price
                    
                    if rebound_ratio >= 0.05:  # 至少5%反弹
                        touch_rebound_count += 1
                        total_rebound_ratio += rebound_ratio
        
        # 指标2：关键转折点（历史低点后趋势反转）
        is_historical_low = False
        trend_reversal_score = 0
        
        # 检查是否为历史低点
        if valley_index > 0:
            historical_min = min(prices[:valley_index])
            if valley_price <= historical_min * 1.05:  # 在历史最低点5%范围内
                is_historical_low = True
        
        # 检查趋势反转
        if valley_index > 10 and valley_index < len(prices) - 10:
            valley_price = prices[valley_index]
            if valley_price > 0:
                # 低点前的趋势
                before_trend = (prices[valley_index-10] - valley_price) / valley_price
                # 低点后的趋势
                after_trend = (prices[valley_index+10] - valley_price) / valley_price
            else:
                before_trend = 0
                after_trend = 0
            
            # 如果前跌后涨，说明是趋势反转
            if before_trend < -0.1 and after_trend > 0.1:
                trend_reversal_score = 1
        
        # 计算综合质量评分
        touch_score = min(touch_rebound_count / 5.0, 1.0)  # 最多5次触及得满分
        rebound_score = min(total_rebound_ratio / 2.0, 1.0)  # 最多200%反弹得满分
        historical_score = 1.0 if is_historical_low else 0.0
        reversal_score = trend_reversal_score
        
        total_score = (touch_score * 0.4 + rebound_score * 0.3 + 
                      historical_score * 0.2 + reversal_score * 0.1)
        
        # 判断是否为有意义的低点
        is_significant = (touch_rebound_count >= 2 or is_historical_low or 
                         trend_reversal_score > 0) and total_score >= 0.3
        
        return {
            'is_significant': is_significant,
            'touch_count': touch_rebound_count,
            'rebound_ratio': total_rebound_ratio / max(touch_rebound_count, 1),
            'is_historical_low': is_historical_low,
            'trend_reversal': trend_reversal_score > 0,
            'total_score': total_score,
            'touch_score': touch_score,
            'rebound_score': rebound_score,
            'historical_score': historical_score,
            'reversal_score': reversal_score
        }

    @staticmethod
    def _calculate_historical_volatility(prices: List[float]) -> float:
        """
        计算历史波动率
        使用日收益率的标准差作为波动率指标
        """
        if len(prices) < 2:
            return 0.0
        
        # 计算日收益率
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                daily_return = (prices[i] - prices[i-1]) / prices[i-1]
                returns.append(daily_return)
        
        if len(returns) < 2:
            return 0.0
        
        # 计算收益率的标准差（年化波动率）
        import statistics
        std_dev = statistics.stdev(returns)
        annualized_volatility = std_dev * (252 ** 0.5)  # 252个交易日
        
        return annualized_volatility

    @staticmethod
    def _get_dynamic_params(volatility: float) -> Dict[str, Any]:
        """
        根据波动率动态调整参数
        """
        if volatility < 0.25:  # 低波动股票
            min_rebound = max(0.08, volatility * 0.6)  # 至少8%，或波动率的60%
            window = 40
            volatility_type = "low"
        elif volatility > 0.6:  # 高波动股票
            min_rebound = 0.20
            window = 15
            volatility_type = "high"
        else:  # 中等波动
            min_rebound = 0.15
            window = 20
            volatility_type = "medium"
        
        return {
            'min_rebound': min_rebound,
            'window': window,
            'volatility_type': volatility_type,
            'volatility': volatility
        }

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
        if low_point_price == 0:
            # 如果低点价格为0，返回默认比例
            return 0.1, 0.05  # 默认上10%下5%
        
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
    def is_slope_sufficient(freeze_data: List[Dict[str, Any]]) -> bool:
        """
        检查slope是否满足最小要求（小于max_invest_slope）
        
        Args:
            freeze_data: 冻结期数据列表
            
        Returns:
            bool: True表示slope满足要求，False表示不满足
        """
        from .strategy_settings import strategy_settings
        
        max_invest_slope = strategy_settings['daily_data_requirements'].get('max_invest_slope', -5)
        
        if len(freeze_data) < 10:
            return False  # 数据不足，不检查
        
        # 计算slope
        slope = HistoricLowService._calculate_slope(freeze_data)
        
        # 检查slope是否小于max_invest_slope（更负）
        return slope < max_invest_slope

    @staticmethod
    def _calculate_slope(klines: List[Dict[str, Any]]) -> float:
        """
        计算股价斜率（价格变化率）
        
        Args:
            klines: 股价数据列表
            
        Returns:
            float: 价格变化率（小数，负数表示下跌）
        """
        if len(klines) < 2:
            return 0.0
        
        # 使用最后10个元素进行斜率检查
        days = min(10, len(klines))
        recent_data = klines[-days:]
        
        # 计算价格变化率
        prices = [float(r['close']) for r in recent_data]
        if len(prices) < 2:
            return 0.0
        
        start_price = prices[0]
        if start_price == 0:
            return 0.0  # 避免除零错误
        
        price_change_ratio = (prices[-1] - start_price) / start_price
        
        return price_change_ratio

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
        
        # 直接使用价格变化率
        if len(prices) > 1:
            start_price = prices[0]
            if start_price == 0:
                price_change_ratio = 0  # 避免除零错误
            else:
                price_change_ratio = (prices[-1] - start_price) / start_price
        else:
            price_change_ratio = 0
        
        # 检查是否过于陡峭下跌（max_slope现在是价格变化率，不是角度）
        # 需要将角度转换为对应的价格变化率
        # 例如：-45度对应-0.5的价格变化率
        max_slope_ratio = max_slope / 90.0  # 将角度转换为价格变化率
        is_too_steep = price_change_ratio < max_slope_ratio
        
        if is_too_steep:
            logger.debug(f"股价斜率过于陡峭: {price_change_ratio*100:.2f}% (限制: {max_slope_ratio*100:.2f}%)")
        
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

    @staticmethod
    def is_wave_completed(all_daily_records: List[Dict[str, Any]], low_point: Dict[str, Any]) -> bool:
        """
        判定从参考低点之后，是否已完成至少一个“谷-峰-回撤”的完整波段：
        - 谷->峰 涨幅 >= min_rise_ratio（默认30%）
        - 峰->回撤 回撤幅度 >= min_retrace_ratio（默认10%）
        - 可选窗口限制：从谷到今天不超过 max_window_days（默认3年≈756交易日），超出仍无完整波则视为长期衰退，返回 False
        """
        if not all_daily_records or not low_point:
            return False
        try:
            min_rise_ratio = float(strategy_settings.get('wave_filter', {}).get('min_rise_ratio', 0.30))
            min_retrace_ratio = float(strategy_settings.get('wave_filter', {}).get('min_retrace_ratio', 0.10))
            max_window_days = int(strategy_settings.get('wave_filter', {}).get('max_window_days', 756))
        except Exception:
            min_rise_ratio, min_retrace_ratio, max_window_days = 0.30, 0.10, 756

        # 找到参考低点日期在全量序列中的索引（取最接近的同日记录）
        ref_date = str(low_point.get('lowest_date') or '')
        if not ref_date:
            return False
        start_idx = None
        for i, rec in enumerate(all_daily_records):
            if str(rec.get('date')) == ref_date:
                start_idx = i
                break
        if start_idx is None:
            # 若找不到精确日期，使用最接近的日期（先前最近）
            for i in range(len(all_daily_records)-1, -1, -1):
                if str(all_daily_records[i].get('date', '')) < ref_date:
                    start_idx = i
                    break
        if start_idx is None:
            return False

        # 限定窗口
        end_idx = min(len(all_daily_records) - 1, start_idx + max_window_days)
        window = all_daily_records[start_idx:end_idx+1]
        if len(window) < 5:
            return False

        low_close = float(window[0].get('close') or 0.0)
        if low_close <= 0:
            return False

        # 谷->峰：取窗口内最高价
        peak_idx = max(range(len(window)), key=lambda k: float(window[k].get('close') or 0.0))
        peak_close = float(window[peak_idx].get('close') or 0.0)
        rise_ratio = (peak_close - low_close) / low_close if low_close > 0 else 0.0
        if rise_ratio < min_rise_ratio:
            return False

        # 峰->回撤：峰后最低价
        if peak_idx >= len(window) - 1:
            return False
        trough_after_peak_close = min(float(r.get('close') or 0.0) for r in window[peak_idx+1:])
        if peak_close <= 0:
            return False
        retrace_ratio = (peak_close - trough_after_peak_close) / peak_close
        return retrace_ratio >= min_retrace_ratio