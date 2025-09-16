#!/usr/bin/env python3
"""
策略实体生成器 - 集中管理所有entity的生成函数
"""
from typing import Dict, List, Any, Tuple
from datetime import datetime

from app.analyzer.strategy.historicLow.strategy_service import HistoricLowService
from app.analyzer.analyzer_service import AnalyzerService
from .strategy_settings import strategy_settings
from app.analyzer.libs.enum.common_enum import InvestmentResult
from app.analyzer.libs.investment.investment_goal_manager import InvestmentGoalManager


class HistoricLowEntity:
    """策略实体生成器 - 集中管理所有entity的生成函数"""
    
    @staticmethod
    def to_opportunity(stock_info: Dict[str, Any], record_of_today: Dict[str, Any], low_point: Dict[str, Any]) -> Dict[str, Any]:
        opportunity = {
            'date': record_of_today.get('date') if record_of_today else None,
            'price': record_of_today.get('close'),
            'lower_bound': low_point.get('invest_lower_bound'),
            'upper_bound': low_point.get('invest_upper_bound'),
            'stock': {
                'id': stock_info.get('id') if stock_info else None,
                'name': stock_info.get('name', '') if stock_info else ''
            },
            'opportunity_record': record_of_today,
            'low_point_ref': low_point,
        }
        
        return opportunity

    @staticmethod
    def to_investment(opportunity: Dict[str, Any]) -> Dict[str, Any]:
        import copy
        
        if not opportunity:
            return None

        # 创建投资目标管理器
        goal_manager = InvestmentGoalManager(strategy_settings['goal'])

        investment = {
            'result': InvestmentResult.OPEN.value,
            'stock': opportunity['stock'],
            'start_date': opportunity['date'],
            'end_date': '',
            'purchase_price': opportunity['price'],
            'tracking': {
                'max_close_reached': { 'price': 0, 'date': '', 'ratio': 0 },
                'min_close_reached': { 'price': 0, 'date': '', 'ratio': 0 },
            },
            'targets': goal_manager.create_investment_targets(),
            'opportunity': opportunity
        }
        
        return investment


    @staticmethod
    def to_session_summary(session_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成会话汇总对象
        
        Args:
            session_results: 会话结果列表，每个元素包含 stock_info 和 investments 列表
            
        Returns:
            Dict[str, Any]: 统一格式的会话汇总对象
        """
        from datetime import datetime
        
        total_investments = 0
        win_count = 0
        loss_count = 0
        open_count = 0
        green_dot_count = 0  # 绿点：盈利 >= 20%
        yellow_dot_count = 0  # 黄点：0% <= 盈利 < 20% 或 平仓
        orange_dot_count = 0  # 橙点：-20% < 亏损 < 0%
        red_dot_count = 0  # 红点：亏损 <= -20%
        total_duration = 0.0
        total_roi = 0.0
        total_profit = 0.0
        total_stocks_with_opportunities = 0

        for stock_result in session_results or []:
            investments = stock_result.get('investments', [])
            if not investments:
                continue
            total_stocks_with_opportunities += 1
            
            for inv in investments:
                purchase_price = float(inv.get('purchase_price', 0))
                profit = float(inv.get('overall_profit', 0))
                duration = float(inv.get('invest_duration_days', 0))
                profit_rate = float(inv.get('overall_profit_rate', 0)) * 100  # 转换为百分比

                total_investments += 1
                total_profit += profit
                total_duration += duration
                
                if purchase_price > 0:
                    total_roi += ((purchase_price + profit) / purchase_price) - 1

                result = inv.get('result')
                if result == InvestmentResult.WIN.value:
                    win_count += 1
                    if profit_rate >= 20:
                        green_dot_count += 1
                    else:
                        yellow_dot_count += 1
                elif result == InvestmentResult.LOSS.value:
                    loss_count += 1
                    if profit_rate > -20:
                        orange_dot_count += 1
                    else:
                        red_dot_count += 1
                elif result == InvestmentResult.OPEN.value:
                    open_count += 1
                    yellow_dot_count += 1

        settled_investments = win_count + loss_count
        avg_duration_days = (total_duration / total_investments) if total_investments > 0 else 0.0
        avg_roi = (total_roi / total_investments) if total_investments > 0 else 0.0
        win_rate = (win_count / settled_investments * 100) if settled_investments > 0 else 0.0
        annual_return = AnalyzerService.get_annual_return(avg_roi, int(avg_duration_days)) if avg_roi != 0 and avg_duration_days > 0 else 0.0
        avg_profit_per_investment = (total_profit / total_investments) if total_investments > 0 else 0.0

        # 计算各颜色点的百分比
        green_dot_rate = (green_dot_count / total_investments * 100) if total_investments > 0 else 0.0
        yellow_dot_rate = (yellow_dot_count / total_investments * 100) if total_investments > 0 else 0.0
        orange_dot_rate = (orange_dot_count / total_investments * 100) if total_investments > 0 else 0.0
        red_dot_rate = (red_dot_count / total_investments * 100) if total_investments > 0 else 0.0

        return {
            'total_investments': total_investments,
            'win_count': win_count,
            'loss_count': loss_count,
            'open_count': open_count,
            'settled_investments': settled_investments,
            'win_rate': round(win_rate, 2),
            'avg_duration_days': round(avg_duration_days, 1),
            'avg_roi': round(avg_roi * 100, 2),
            'annual_return': round(annual_return, 2),
            'avg_annual_return': round(annual_return, 2),
            'total_profit': round(total_profit, 2),
            'avg_profit_per_investment': round(avg_profit_per_investment, 2),
            'total_stocks_with_opportunities': total_stocks_with_opportunities,
            'green_dot_count': green_dot_count,
            'yellow_dot_count': yellow_dot_count,
            'orange_dot_count': orange_dot_count,
            'red_dot_count': red_dot_count,
            'green_dot_rate': round(green_dot_rate, 1),
            'yellow_dot_rate': round(yellow_dot_rate, 1),
            'orange_dot_rate': round(orange_dot_rate, 1),
            'red_dot_rate': round(red_dot_rate, 1),
            'summary_generated_at': datetime.now().isoformat()
        }

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

        low_point_config = strategy_settings.get('low_point_invest_range')

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