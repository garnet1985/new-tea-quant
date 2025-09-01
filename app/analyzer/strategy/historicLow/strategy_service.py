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
    def find_historic_low_points(daily_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        使用简单算法：从当前数据倒推指定年份，取到它们的最低点
        """
        if not daily_records or len(daily_records) < 2000:  # 至少需要足够的历史数据
            return []
        
        low_points = []
        current_date = daily_records[-1]['date']
        
        # 从settings获取回溯年份，过滤掉0
        years_to_lookback = [year for year in strategy_settings['daily_data_requirements']['low_points_ref_years'] if year > 0]
        
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
    def find_strong_valleys(valleys: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not valleys:
            return []
            
        grouped_valleys = HistoricLowService.group_valleys(valleys)

        strong_valleys = HistoricLowService.filter_strong_valleys(grouped_valleys)
        
        return strong_valleys;


    @staticmethod
    def filter_strong_valleys(grouped_valleys: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not grouped_valleys:
            return []

        min_touch_count = strategy_settings['valley_analysis']['min_touch_count']

        candidates = []
        for g in grouped_valleys:
            vmin = float(g['min'])
            vmax = float(g['max'])
            touches = len(g.get('items', [])) or len(g.get('values', []))

            # 硬性过滤：触及次数和波动范围
            if touches < min_touch_count:
                continue

            if (vmax - vmin) / vmin > strategy_settings['valley_analysis']['max_amplitude_range']:
                continue

            # 统一输出结构
            items = g.get('items', [])
            dates = [it.get('date') for it in items if 'date' in it]
            candidates.append({
                'min': vmin,
                'max': vmax,
                'avg': (vmin + vmax) / 2.0,
                'valley_amplitude_range': (vmax - vmin) / vmin,
                'touch_count': touches,
                'valley_dates': dates,
                # 'refs': items
            })

        # 排序并取前3
        candidates.sort(key=lambda x: x['touch_count'], reverse=True)
        return candidates[:3]


    @staticmethod
    def group_valleys(valleys: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not valleys or len(valleys) == 0:
            return []
        
        # 单次遍历构建聚类（5%阈值），不排序
        threshold = strategy_settings['valley_analysis']['cluster_threshold']

        grouped_valleys: List[Dict[str, Any]] = []
        for v in valleys:
            p = float(v['price'])
            placed = False
            for group_valley in grouped_valleys:
                # 试探加入后组跨度是否仍在阈值内
                new_min = p if p < group_valley['min'] else group_valley['min']
                new_max = p if p > group_valley['max'] else group_valley['max']
                span_pct = ((new_max - new_min) / new_min) if new_min > 0 else 0.0
                if span_pct <= threshold:
                    group_valley['min'] = new_min
                    group_valley['max'] = new_max
                    group_valley['values'].append(p)
                    group_valley['items'].append(v)
                    placed = True
                    break
            if not placed:
                grouped_valleys.append({'min': p, 'max': p, 'values': [p], 'items': [v]})

        return grouped_valleys;


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
        price_range_config = strategy_settings.get('price_range', {})
        base_ratio = price_range_config.get('base_ratio', 0.025)
        min_absolute_range = price_range_config.get('min_absolute_range', 0.2)
        max_absolute_range = price_range_config.get('max_absolute_range', 10.0)
        
        # 基础区间（上下各base_ratio）
        base_absolute_range = low_point_price * base_ratio
        
        # 如果基础区间小于最小区间，则使用最小区间
        if base_absolute_range < min_absolute_range:
            absolute_range = min_absolute_range
        # 如果基础区间大于最大区间，则使用最大区间
        elif base_absolute_range > max_absolute_range:
            absolute_range = max_absolute_range
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
                    'date': low_date,
                    'price_range': low_point['price_range']
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
        先计算止盈，再计算止损
        """
        current_price = float(record_of_today['close'])

        if not freeze_data or not daily_records:
            return None

        min_price = min(freeze_data, key=lambda x: float(x['close']))['close']
        max_price = max(freeze_data, key=lambda x: float(x['close']))['close']

        if min_price < low_point['min']:
            return None

        # dates_touched_valley = low_point.get('valley_dates', [])

        # start_date = min(dates_touched_valley)
        # end_date = max(dates_touched_valley)

        # duration_in_years = HistoricLowService.get_year_duration(start_date, end_date)
        
        # if len(dates_touched_valley) > 1:
            
        #     # 在这个时间范围内找出所有日线的最高价和最低价
        #     prices_in_range = []
        #     for record in daily_records:
        #         if start_date <= record['date'] <= end_date:
        #             prices_in_range.append(float(record['close']))
            
        #     if prices_in_range:
        #         min_price = min(prices_in_range)
        #         max_price = max(prices_in_range)

        # else:
        #     min_price = float(low_point['min'])
        #     max_price = float(low_point['max'])
        

        # amplitude_ratio = (max_price - min_price) / min_price

        # logger.info(f"🎯 计算投资目标: {max_price} {min_price} {amplitude_ratio}")

        # if amplitude_ratio > strategy_settings['goal']['take_profit']['max_ration']:
        #     amplitude_ratio = strategy_settings['goal']['take_profit']['max_ration']

        # logger.info(f"🎯 计算投资目标: {amplitude_ratio}")
        
        # # 计算止盈比例（历史波动率的某个百分比，但有封顶）
        # calculated_win_ratio = amplitude_ratio * strategy_settings['goal']['take_profit']['profit_ratio']
        
        # # 应用封顶机制
        # take_profit_ratio = min(calculated_win_ratio, amplitude_ratio)

        take_profit_ratio = 0.4;
        
        # 计算止损比例（止盈除以divider）
        stop_loss_divider = strategy_settings['goal']['stop_loss']['divider']
        stop_loss_ratio = take_profit_ratio / stop_loss_divider
        
        # 计算具体价格
        stop_loss_price = current_price * (1 - stop_loss_ratio)
        take_profit_price = current_price * (1 + take_profit_ratio)

        
        return {
            'stop_loss_price': stop_loss_price,
            'take_profit_price': take_profit_price,
            'stop_loss_ratio': stop_loss_ratio,
            'take_profit_ratio': take_profit_ratio
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
    def to_investment(opportunity: Dict[str, Any], investment_targets: Dict[str, Any]) -> Dict[str, Any]:
        """
        将机会转换为投资对象，包含投资目标
        """
        # 检查止损是否满足最小要求
        min_stop_loss_ratio = strategy_settings['goal']['stop_loss']['min_ratio']
        calculated_stop_loss_ratio = investment_targets['stop_loss_ratio']
        
        if calculated_stop_loss_ratio < min_stop_loss_ratio:
            return None  # 止损太小，忽略这个投资
        
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
            'investment_targets': investment_targets
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