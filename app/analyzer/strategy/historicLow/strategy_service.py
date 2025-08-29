import pprint
import math
from typing import Dict, List, Any, Tuple
from typing_extensions import Optional

from loguru import logger
from .strategy_settings import strategy_settings as invest_settings
from app.analyzer.analyzer_service import AnalyzerService
from datetime import datetime


class HistoricLowService:
    """HistoricLow策略的静态服务类"""

    @staticmethod
    def find_historic_low_points(daily_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:

        # # 1. 使用settings中的low_points_ref_years动态获取不同年限的低点
        # from app.analyzer.strategy.historicLow.strategy_settings import strategy_settings
        # low_points_ref_years = strategy_settings['daily_data_requirements']['low_points_ref_years']
        
        # low_points = []
        # for years in low_points_ref_years:
        #     valleys = HistoricLowService.find_valleys_fallback(daily_records, years)
        #     low_points.extend(valleys)


        valleys = AnalyzerService.find_valleys(daily_records, invest_settings['valley_analysis']['min_drop_threshold'], invest_settings['valley_analysis']['local_range_days'], invest_settings['valley_analysis']['lookback_days']);

        low_points = HistoricLowService.find_strong_valleys(valleys)



    @staticmethod
    def find_strong_valleys(valleys: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        grouped_valleys = HistoricLowService.group_valleys(valleys)

        strong_valleys = HistoricLowService.filter_strong_valleys(grouped_valleys)

        pprint.pprint(strong_valleys)
        
        return strong_valleys;

        # return merged_lows;

    @staticmethod
    def filter_strong_valleys(grouped_valleys: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not grouped_valleys:
            return []

        min_touch_count = invest_settings['valley_analysis']['min_touch_count']

        candidates = []
        for g in grouped_valleys:
            vmin = float(g['min'])
            vmax = float(g['max'])
            touches = len(g.get('items', [])) or len(g.get('values', []))

            # 硬性过滤：触及次数和波动范围
            if touches < min_touch_count:
                continue

            if (vmax - vmin) / vmin > invest_settings['valley_analysis']['max_amplitude_range']:
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
            return None
        
        # 单次遍历构建聚类（5%阈值），不排序
        threshold = invest_settings['valley_analysis']['cluster_threshold']

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
    def calc_min_loss_rate(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        lowest, highest = HistoricLowService.find_extreme_price(records)
        amplitude = highest / lowest - 1;
        lowest_loss_rate = amplitude / 40;
        return lowest_loss_rate;



    @staticmethod
    def is_meet_strategy_requirements(daily_data: List[Dict[str, Any]]) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        规则：
        1) 寻找最后一个包含负值价格的记录索引（close/highest/lowest 任一为负）
        2) 取该索引之后的连续片段作为有效序列
        3) 判断该连续片段长度是否满足配置中的最小所需日线数
        """
        if not daily_data:
            return False, []

        last_negative_idx = -1
        for idx, rec in enumerate(daily_data):
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

        # 取连续片段（最后一个负值之后）
        continuous_slice = daily_data[last_negative_idx + 1:] if last_negative_idx + 1 < len(daily_data) else []

        from app.analyzer.strategy.historicLow.strategy_settings import strategy_settings as _settings
        min_required = _settings.get('daily_data_requirements', {}).get('min_required_daily_records', 2000)
        return len(continuous_slice) >= min_required, continuous_slice



    
    @staticmethod
    def is_in_invest_range(record, low_point):
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
    
    @staticmethod    
    def get_previous_low_points(record, all_historic_lows):
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

























    


    @staticmethod
    def to_opportunity(stock: Dict[str, Any],
                       record_of_today: Dict[str, Any],
                       investment_targets: Dict[str, Any],
                       low_point: Dict[str, Any],
                       previous_low_points: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        构造统一的机会对象，保证结构一致。
        所有数值字段统一转换为float类型。
        """
        opportunity = {
            'stock': {
                'id': stock.get('id') if stock else None,
                'name': stock.get('name', '') if stock else ''
            },
            'opportunity_record': record_of_today,
            'goal': {
                'loss': investment_targets.get('stop_loss_price'),
                'win': investment_targets.get('take_profit_price'),
                'purchase': record_of_today.get('close') if record_of_today else None
            },
            'historic_low_ref': low_point,
            'investment_targets': investment_targets,
            'previous_low_points': previous_low_points or [],
            'invest_start_date': record_of_today.get('date') if record_of_today else None
        }
        
        return opportunity

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
    def set_loss(record):
        return float(record['close']) * invest_settings['goal']['loss']
    
    @staticmethod
    def set_win(record):
        return float(record['close']) * invest_settings['goal']['win']



    @staticmethod
    def is_reached_min_required_daily_records(daily_records):
        """
        检查是否达到最小所需日线记录数
        
        新逻辑：需要至少2000条日线记录
        """
        return len(daily_records) >= invest_settings['daily_data_requirements']['min_required_daily_records']



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
        freeze_days = invest_settings['daily_data_requirements']['freeze_period_days']
        
        # 分割数据
        freeze_records = daily_data[-freeze_days:]  # 最近200个交易日（冻结期）
        history_records = daily_data[:-freeze_days]  # 之前的数据（历史期）

        return freeze_records, history_records