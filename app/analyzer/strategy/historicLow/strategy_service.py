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

        valleys = AnalyzerService.find_valleys(daily_records, strategy_settings['valley_analysis']['min_drop_threshold'], strategy_settings['valley_analysis']['local_range_days'], strategy_settings['valley_analysis']['lookback_days']);

        low_points = HistoricLowService.find_strong_valleys(valleys)
        
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
    def is_in_invest_range(record, low_point):
        if low_point is None:
            return False
        # return record['close'] < low_point['max'] and record['close'] > low_point['min']
        return record['close'] < low_point['min'] * 1.05 and record['close'] > low_point['min'] * 0.95
    
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
    def calculate_investment_targets(record_of_today: Dict[str, Any], low_point: Dict[str, Any], daily_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算投资目标：止损和止盈价格
        先计算止盈，再计算止损
        """
        current_price = float(record_of_today['close'])

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