import pprint
import math
from typing import Dict, List, Any, Tuple
from typing_extensions import Optional

from loguru import logger
from .strategy_settings import strategy_settings
from app.analyzer.analyzer_service import AnalyzerService
from datetime import datetime


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
                if stage.get('is_dynamic_loss', False):
                    loss_ratio = stage.get('loss_ratio', 0)
                    if loss_ratio > 0.5:  # 动态止损比例不应超过50%
                        errors.append(f"动态止损比例({loss_ratio:.1%})过高")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def calculate_volatility(daily_records: List[Dict[str, Any]], days: int = 100) -> float:
        """
        计算股票的历史波动率（年化）
        
        Args:
            daily_records: 日线数据
            days: 计算天数，默认100天
            
        Returns:
            float: 年化波动率
        """
        if len(daily_records) < days:
            days = len(daily_records)
        
        # 取最近days天的数据
        recent_data = daily_records[-days:]
        
        # 计算日收益率
        returns = []
        for i in range(1, len(recent_data)):
            prev_price = float(recent_data[i-1]['close'])
            curr_price = float(recent_data[i]['close'])
            daily_return = (curr_price - prev_price) / prev_price
            returns.append(daily_return)
        
        if not returns:
            return 0.0
        
        # 计算年化波动率
        import statistics
        daily_volatility = statistics.stdev(returns)
        annual_volatility = daily_volatility * (252 ** 0.5)  # 年化
        
        return annual_volatility
    
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
        使用简单算法：从当前数据倒推指定年份，取到它们的最低点
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
            
            # 计算投资范围（上下5%）
            range_min = min_price * 0.95
            range_max = min_price * 1.05
            
            low_points.append({
                'min': range_min,
                'max': range_max,
                'avg': min_price,
                'valley_amplitude_range': 0.10,  # 5%上下 = 10%范围
                'touch_count': 1,  # 每个年份只有一个最低点
                'valley_dates': [min_date],
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
    def calculate_dynamic_price_range(low_point_price: float) -> float:
        """
        计算动态价格区间比例
        
        Args:
            low_point_price: 历史低点价格
            
        Returns:
            float: 价格区间比例
        """
        # 从settings获取配置
        low_point_config = strategy_settings.get('low_point_invest_range', {})
        base = low_point_config.get('base', 0.05)
        min_range = low_point_config.get('min', 0.2)
        max_range = low_point_config.get('max', 10.0)
        
        # 基础区间（上下各base比例）
        base_absolute_range = low_point_price * base
        
        # 如果基础区间小于最小区间，则使用最小区间
        if base_absolute_range < min_range:
            absolute_range = min_range
        # 如果基础区间大于最大区间，则使用最大区间
        elif base_absolute_range > max_range:
            absolute_range = max_range
        else:
            absolute_range = base_absolute_range
        
        # 计算对应的比例（上下各absolute_range，总共2*absolute_range）
        price_range_ratio = absolute_range / low_point_price
        
        return price_range_ratio
    
    @staticmethod
    def is_in_invest_range(record, low_point, freeze_data=None):
        """
        检查是否在投资范围内
        新增条件：在freeze data内没有出现比历史低点更低的价格
        """
        if low_point is None:
            return False
        
        current_price = float(record['close'])
        low_point_price = float(low_point['min'])  # 历史低点价格
        
        # 计算动态价格区间
        price_range_ratio = HistoricLowService.calculate_dynamic_price_range(low_point_price)
        lower_bound = low_point_price * (1 - price_range_ratio)
        upper_bound = low_point_price * (1 + price_range_ratio)
        
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
            
            # 条件2：如果freeze data的最低点已经在历史低点上方10%范围内，说明已经有过反弹，也不投资
            # if freeze_min_price > low_point_price * 1.10:
            #     return False
            
            # 条件3：当前价格不应该比freeze data的最低点高出太多（超过5%）
            if current_price > freeze_min_price * 1.05:
                return False
        
        # 新增条件：检查当前是否在连续下跌过程中
        if freeze_data and HistoricLowService.is_in_continuous_downtrend(record, freeze_data):
            return False
        
        return True

    @staticmethod
    def is_in_continuous_downtrend(record: Dict[str, Any], freeze_data: List[Dict[str, Any]]) -> bool:
        """
        检查当前是否处于连续下跌过程中，分析整个freeze data期间的趋势变化
        
        Args:
            record: 当前记录
            freeze_data: 冻结期数据
            
        Returns:
            bool: True表示在连续下跌中，False表示不在连续下跌中
        """
        if not freeze_data or len(freeze_data) < 10:
            return False
        
        # 获取所有价格数据
        all_prices = [float(r['close']) for r in freeze_data]
        
        # 1. 检查整个freeze data期间是否处于下跌趋势
        start_price = all_prices[0]
        end_price = all_prices[-1]
        total_drop_rate = (start_price - end_price) / start_price
        
        # 如果整体跌幅超过20%，需要进一步分析趋势变化
        if total_drop_rate > 0.20:
            # 2. 分析趋势变化：将freeze data分为前1/3、中1/3、后1/3三段
            segment_size = len(all_prices) // 3
            if segment_size < 3:
                return True  # 数据不足，保守处理
            
            first_segment = all_prices[:segment_size]
            middle_segment = all_prices[segment_size:2*segment_size]
            last_segment = all_prices[2*segment_size:]
            
            # 计算各段的平均价格
            first_avg = sum(first_segment) / len(first_segment)
            middle_avg = sum(middle_segment) / len(middle_segment)
            last_avg = sum(last_segment) / len(last_segment)
            
            # 3. 检查趋势是否在变缓
            first_to_middle_drop = (first_avg - middle_avg) / first_avg
            middle_to_last_drop = (middle_avg - last_avg) / middle_avg
            
            # 如果中段到后段的跌幅明显小于前段到中段的跌幅，说明趋势在变缓
            if middle_to_last_drop < first_to_middle_drop * 0.5:
                # 趋势在变缓，进一步检查最近的表现
                return HistoricLowService._check_recent_performance(all_prices)
            else:
                # 趋势仍在加速下跌
                return True
        
        # 4. 检查最近的表现（最近5天）
        return HistoricLowService._check_recent_performance(all_prices)
    
    @staticmethod
    def _check_recent_performance(prices: List[float]) -> bool:
        """
        检查最近5天的表现
        
        Args:
            prices: 价格列表
            
        Returns:
            bool: True表示仍在下跌中，False表示可能企稳
        """
        if len(prices) < 5:
            return False
        
        recent_prices = prices[-5:]
        
        # 计算下跌天数
        down_days = 0
        for i in range(1, len(recent_prices)):
            if recent_prices[i] < recent_prices[i-1]:
                down_days += 1
        
        # 如果最近5天中有3天或以上在下跌，认为是连续下跌趋势
        if down_days >= 3:
            return True
        
        # 检查最近3天是否连续下跌
        if len(recent_prices) >= 3:
            if (recent_prices[-3] > recent_prices[-2] > recent_prices[-1]):
                return True
        
        # 检查最近两天的累计跌幅
        if len(recent_prices) >= 2:
            two_days_ago = recent_prices[-2]
            today = recent_prices[-1]
            two_day_drop_rate = (two_days_ago - today) / two_days_ago
            
            # 如果两天累计跌幅超过8%，认为是急速下跌
            if two_day_drop_rate > 0.08:
                return True
        
        # 检查最近5天的累计跌幅
        if len(recent_prices) >= 5:
            five_days_ago = recent_prices[0]
            today = recent_prices[-1]
            five_day_drop_rate = (five_days_ago - today) / five_days_ago
            
            # 如果5天累计跌幅超过15%，认为是明显下跌趋势
            if five_day_drop_rate > 0.15:
                return True
        
        return False
    
    @staticmethod    
    def get_previous_low_points(record, all_historic_lows):
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
                    'date': low_date
                })
        
        # 按价格从低到高排序
        previous_lows.sort(key=lambda x: x['price'])
        
        return previous_lows


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
    def get_year_duration(start_date, end_date) -> Dict[str, Any]:
        if not start_date or not end_date:
            return 1

        start_year = int(start_date[:4])
        end_year = int(end_date[:4])
        duration_in_years = end_year - start_year + 1

        return duration_in_years




    @staticmethod
    def calculate_investment_targets(record_of_today: Dict[str, Any], low_point: Dict[str, Any], freeze_data: List[Dict[str, Any]], daily_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算投资目标：止损和止盈价格
        使用新的分段平仓策略配置
        """
        current_price = float(record_of_today['close'])

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
        initial_stop_loss_ratio = initial_stop_loss_stage['loss_ratio']
        
        # 获取最后一个止盈阶段作为最大止盈目标
        take_profit_stages = goal_config['take_profit']['stages']
        max_take_profit_stage = take_profit_stages[-1]  # 最后一个阶段
        max_take_profit_ratio = max_take_profit_stage['win_ratio']
        
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
        """
        构造统一的机会对象，保证结构一致。
        所有数值字段统一转换为float类型。
        """
        opportunity = {
            'date': record_of_today.get('date') if record_of_today else None,
            'price': record_of_today.get('close'),
            'opportunity_record': record_of_today,
            'valley_ref': low_point,
            'stock': {
                'id': stock_info.get('id') if stock_info else None,
                'name': stock_info.get('name', '') if stock_info else ''
            }
        }
        
        return opportunity

    @staticmethod
    def to_investment(opportunity: Dict[str, Any], investment_targets: Dict[str, Any], freeze_data: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        将机会转换为投资对象，包含投资目标
        """
        # 检查止损是否满足最小要求（使用初始止损阶段）
        goal_config = strategy_settings['goal']
        initial_stop_loss_stage = goal_config['stop_loss']['stages'][0]
        min_stop_loss_ratio = initial_stop_loss_stage['loss_ratio']
        calculated_stop_loss_ratio = investment_targets['stop_loss_ratio']
        
        if calculated_stop_loss_ratio < min_stop_loss_ratio:
            return None  # 止损太小，忽略这个投资
        
        # 计算freeze data统计信息
        freeze_stats = HistoricLowService.calculate_freeze_data_stats(freeze_data) if freeze_data else {}
        
        investment = {
            'invest_start_date': opportunity['date'],
            'purchase': opportunity['price'],
            'opportunity_record': opportunity['opportunity_record'],
            'valley_ref': opportunity['valley_ref'],
            'stock': opportunity['stock'],
            'goal': {
                'loss': investment_targets['stop_loss_price'],
                'win': investment_targets['take_profit_price'],
                'purchase': opportunity['price']
            },
            'investment_targets': investment_targets,
            # 新增：持有期间的最高/最低价追踪（初始值为买入价）
            'period_max_close': opportunity['price'],
            'period_max_close_date': opportunity['date'],
            'period_min_close': opportunity['price'],
            'period_min_close_date': opportunity['date'],
            # 新增：历史低点信息，用于JSON记录
            'historic_low_ref': {
                'lowest_price': opportunity['valley_ref']['min'],
                'lowest_date': opportunity['valley_ref'].get('min_date', ''),
                'conclusion_from': opportunity['valley_ref'].get('valley_dates', [])
            },
            # 新增：freeze data统计信息
            'freeze_data_stats': freeze_stats,
            # 新增：分段平仓相关字段
            'staged_exit': {
                'enabled': True,
                'current_position_ratio': 1.0,  # 当前持仓比例
                'breakeven_stop_loss': False,  # 是否已移动到不亏不赚止损
                'trailing_stop_price': None,  # 动态止损价格
                'last_close_price': opportunity['price'],  # 前一次close价格
                'exited_stages': [],  # 已执行的平仓阶段
                'total_realized_profit': 0.0,  # 累计已实现收益
                'total_realized_profit_rate': 0.0  # 累计已实现收益率
            }
        }
        
        return investment

    @staticmethod
    def to_session_summary(session_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        total = 0
        win = 0
        loss = 0
        open_ = 0
        total_duration = 0.0
        total_roi = 0.0
        total_profit = 0.0
        total_investment_amount = 0.0
        stocks_with_opps = 0

        for stock_result in session_results or []:
            investments = (stock_result.get('investments') or {}).values()
            if not investments:
                continue
            stocks_with_opps += 1
            for inv in investments:
                res = inv.get('result') or {}
                inv_ref = inv.get('investment_ref') or {}
                goal = (inv_ref.get('goal') or {})
                purchase = float(goal.get('purchase') or 0)
                profit = float(res.get('profit') or 0)
                duration = float(res.get('invest_duration_days') or 0)

                total += 1
                total_profit += profit
                total_duration += duration
                if purchase > 0:
                    total_investment_amount += purchase
                    total_roi += ((purchase + profit) / purchase) - 1

                r = res.get('result')
                if r == 'win':
                    win += 1
                elif r == 'loss':
                    loss += 1
                elif r == 'open':
                    open_ += 1

        avg_duration_days = (total_duration / total) if total > 0 else 0.0
        avg_roi = (total_roi / total) if total > 0 else 0.0
        settled = win + loss
        win_rate = (win / settled * 100) if settled > 0 else 0.0
        annual_return = ((1 + avg_roi) ** (365 / avg_duration_days) - 1) * 100 if avg_roi != 0 and avg_duration_days > 0 else 0.0
        avg_profit_per_investment = (total_profit / total) if total > 0 else 0.0

        return {
            'total_investments': total,
            'win_count': win,
            'loss_count': loss,
            'open_count': open_,
            'settled_investments': settled,
            'win_rate': round(win_rate, 2),
            'avg_duration_days': round(avg_duration_days, 1),
            'avg_roi': round(avg_roi * 100, 2),
            'annual_return': round(annual_return, 2),
            'total_profit': round(total_profit, 2),
            'avg_profit_per_investment': round(avg_profit_per_investment, 2),
            'total_stocks_with_opportunities': stocks_with_opps
        }

    @staticmethod
    def to_stock_summary(stock_simulation_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        从单只股票的模拟结果构造统一的股票级汇总。
        stock_result 形如 { 'stock_info': {..., 'id': ...}, 'investments': {...} }
        """
        stock_id = (stock_simulation_result.get('stock_info') or {}).get('id')
        investments = list((stock_simulation_result.get('investments') or {}).values())

        total_investments = len(investments)
        success_count = len([inv for inv in investments if (inv.get('result') or {}).get('result') == 'win'])
        fail_count = len([inv for inv in investments if (inv.get('result') or {}).get('result') == 'loss'])
        open_count = len([inv for inv in investments if (inv.get('result') or {}).get('result') == 'open'])

        total_profit = sum([float((inv.get('result') or {}).get('profit') or 0.0) for inv in investments])
        avg_profit = (total_profit / total_investments) if total_investments > 0 else 0.0

        total_duration = sum([float((inv.get('result') or {}).get('invest_duration_days') or 0.0) for inv in investments])
        avg_duration = (total_duration / total_investments) if total_investments > 0 else 0.0

        win_rate = (success_count / total_investments * 100) if total_investments > 0 else 0.0

        return {
            'stock_id': stock_id,
            'total_investments': total_investments,
            'success_count': success_count,
            'fail_count': fail_count,
            'open_count': open_count,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'avg_profit': avg_profit,
            'avg_duration_days': avg_duration,
            'investments': investments
        }

    @staticmethod
    def get_investing(stock, investing_stocks):
        return investing_stocks.get(stock['id'])


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