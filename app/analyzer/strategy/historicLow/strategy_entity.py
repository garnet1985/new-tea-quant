#!/usr/bin/env python3
"""
策略实体生成器 - 集中管理所有entity的生成函数
"""
import pprint
from typing import Dict, List, Any, Tuple
from datetime import datetime

from app.data_source.data_source_service import DataSourceService
from .strategy_settings import strategy_settings
from .strategy_enum import InvestmentResult
from app.analyzer.strategy.historicLow import strategy_enum


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
        if not opportunity:
            return None

        investment = {
            'result': strategy_enum.InvestmentResult.OPEN.value,
            'stock': opportunity['stock'],
            'start_date': opportunity['date'],
            'end_date': '',
            'purchase_price': opportunity['price'],
            'tracking': {
                'max_close_reached': { 'price': 0, 'date': '', 'ratio': 0 },
                'min_close_reached': { 'price': 0, 'date': '', 'ratio': 0 },
            },
            'targets': {
                'investment_ratio_left': 1.0,
                'is_breakeven': False,
                'is_dynamic_stop_loss': False,
                'all': {
                    'stop_loss': strategy_settings['goal']['stop_loss'],
                    'take_profit': strategy_settings['goal']['take_profit']['stages']
                },
                'completed': [],
            },
            'opportunity': opportunity
        }
        
        return investment

    # @staticmethod
    # def to_target(target_name: str, is_achieved: bool, profit: float, profit_rate: float, 
    #               profit_weight: float, duration: int, sell_date: str, sell_price: float) -> Dict[str, Any]:
    #     """
    #     生成统一的target对象
        
    #     Args:
    #         name: 目标收益率（字符串，如 "10%" 或 "break_even"）
    #         is_achieved: 是否达成
    #         profit: 利润
    #         profit_rate: 利润率
    #         profit_weight: 利润权重
    #         duration: 持续时间
    #         sell_date: 卖出日期
    #         sell_price: 卖出价格
            
    #     Returns:
    #         Dict[str, Any]: 统一格式的target对象
    #     """
    #     return {
    #         'name': target_name,
    #         'is_achieved': is_achieved,
    #         'profit': round(profit, 4),
    #         'profit_rate': round(profit_rate, 6),
    #         'profit_weight': round(profit_weight, 6),
    #         'duration': duration,
    #         'sell_date': sell_date,
    #         'sell_price': round(sell_price, 4)
    #     }

    @staticmethod
    def to_record(stock_info: Dict[str, Any], investment_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成统一的投资记录对象
        
        Args:
            stock_info: 股票信息
            investment_history: 投资历史记录
            
        Returns:
            Dict[str, Any]: 统一格式的投资记录对象
        """
        # 计算统计信息（顶层唯一 statistics）
        total_investments = len(investment_history)
        success_count = len([inv for inv in investment_history if inv.get('status') == InvestmentResult.WIN.value])
        fail_count = len([inv for inv in investment_history if inv.get('status') == InvestmentResult.LOSS.value])
        open_count = len([inv for inv in investment_history if inv.get('status') == InvestmentResult.OPEN.value])
        win_rate = (success_count / total_investments * 100) if total_investments > 0 else 0.0
        total_profit = sum([inv.get('profit', 0) for inv in investment_history])
        avg_profit = total_profit / total_investments if total_investments > 0 else 0.0
        durations = [inv.get('invest_duration_days', 0) for inv in investment_history if inv.get('invest_duration_days')]
        avg_duration_days = sum(durations) / len(durations) if durations else 0.0
        
        # 计算平均ROI和年化收益率
        total_roi = 0.0
        total_purchase_amount = 0.0
        for inv in investment_history:
            purchase_price = inv.get('purchase_price', 0)
            profit = inv.get('profit', 0)
            if purchase_price > 0:
                total_purchase_amount += purchase_price
                total_roi += ((purchase_price + profit) / purchase_price) - 1
        
        avg_roi = (total_roi / total_investments * 100) if total_investments > 0 else 0.0
        avg_annual_return = ((1 + total_roi / total_investments) ** (365 / avg_duration_days) - 1) * 100 if total_investments > 0 and avg_duration_days > 0 else 0.0

        per_stock_stats = {
            'total_investments': total_investments,
            'success_count': success_count,
            'fail_count': fail_count,
            'open_count': open_count,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'avg_profit': avg_profit,
            'avg_duration_days': avg_duration_days,
            'avg_roi': round(avg_roi, 2),
            'avg_annual_return': round(avg_annual_return, 2)
        }

        # 构建记录数据
        record = {
            'stock_info': {
                'id': stock_info.get('id', ''),
                'name': stock_info.get('name', ''),
                'industry': stock_info.get('industry', '')
            },
            'results': investment_history,
            'statistics': per_stock_stats
        }
        
        return record

    @staticmethod
    def to_settlement(stock_info: Dict[str, Any], settlement_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成统一格式的投资结算信息字典
        
        Args:
            stock_info: 股票信息
            settlement_info: 结算信息
            
        Returns:
            Dict[str, Any]: 统一格式的结算信息字典
        """
        # 返回统一格式的结算信息，不生成文件
        return {
            'status': settlement_info.get('result', ''),
            'start_date': settlement_info.get('start_date', ''),
            'end_date': settlement_info.get('end_date', ''),
            'profit': settlement_info.get('profit', 0),  # 添加profit字段
            'invest_duration_days': settlement_info.get('invest_duration_days', 0),  # 添加duration字段
            'overall_profit_rate': settlement_info.get('overall_profit_rate'),
            'purchase_price': (settlement_info.get('investment') or {}).get('purchase_price'),
            'investment': {
                'targets': ((settlement_info.get('investment') or {}).get('targets') or [])
            },
            'tracks': settlement_info.get('tracks', {}),
            'slope_info': settlement_info.get('slope_info', {}),
            'pre_invest_series': settlement_info.get('pre_invest_series', {}),
            'historic_low_ref': {
                'term': (settlement_info.get('historic_low_ref') or {}).get('term'),
                'date': (settlement_info.get('historic_low_ref') or {}).get('date'),
                'price': (settlement_info.get('historic_low_ref') or {}).get('price')
            }
        }

    @staticmethod
    def to_session_summary(session_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成会话汇总对象
        
        Args:
            session_results: 会话结果列表
            
        Returns:
            Dict[str, Any]: 统一格式的会话汇总对象
        """
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
                inv_ref = inv.get('investment_ref') or {}
                goal = (inv_ref.get('goal') or {})
                purchase = float(goal.get('purchase') or 0)
                profit = float(inv.get('overall_profit') or 0)
                duration = float(inv.get('invest_duration_days') or 0)

                total += 1
                total_profit += profit
                total_duration += duration
                if purchase > 0:
                    total_investment_amount += purchase
                    total_roi += ((purchase + profit) / purchase) - 1

                r = inv.get('result')
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
            'avg_annual_return': round(annual_return, 2),  # 添加avg_annual_return字段
            'total_profit': round(total_profit, 2),
            'avg_profit_per_investment': round(avg_profit_per_investment, 2),
            'total_stocks_with_opportunities': stocks_with_opps
        }

    @staticmethod
    def to_stock_summary(stock_simulation_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        从单只股票的模拟结果构造统一的股票级汇总。
        
        Args:
            stock_simulation_result: 股票模拟结果
            
        Returns:
            Dict[str, Any]: 统一格式的股票汇总对象
        """
        stock_id = (stock_simulation_result.get('stock_info') or {}).get('id')
        investments = list((stock_simulation_result.get('investments') or {}).values())

        total_investments = len(investments)
        success_count = len([inv for inv in investments if inv.get('result') == 'win'])
        fail_count = len([inv for inv in investments if inv.get('result') == 'loss'])
        open_count = len([inv for inv in investments if inv.get('result') == 'open'])

        total_profit = sum([float(inv.get('overall_profit') or 0.0) for inv in investments])
        avg_profit = (total_profit / total_investments) if total_investments > 0 else 0.0

        total_duration = sum([float(inv.get('invest_duration_days') or 0.0) for inv in investments])
        avg_duration = (total_duration / total_investments) if total_investments > 0 else 0.0

        win_rate = (success_count / total_investments * 100) if total_investments > 0 else 0.0

        # 计算平均ROI和年化收益率
        total_roi = 0.0
        for inv in investments:
            purchase_price = float(inv.get('purchase_price') or 0.0)
            profit = float(inv.get('overall_profit') or 0.0)
            if purchase_price > 0:
                total_roi += ((purchase_price + profit) / purchase_price) - 1
        
        avg_roi = (total_roi / total_investments * 100) if total_investments > 0 else 0.0
        avg_annual_return = ((1 + total_roi / total_investments) ** (365 / avg_duration) - 1) * 100 if total_investments > 0 and avg_duration > 0 else 0.0

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
            'avg_roi': round(avg_roi, 2),
            'avg_annual_return': round(avg_annual_return, 2),
            'investments': investments
        }

    @staticmethod
    def to_job_data(stock_id: str, last_update: str, is_in_db: bool) -> Dict[str, Any]:
        """
        生成任务数据对象
        
        Args:
            stock_id: 股票ID
            last_update: 最后更新时间
            is_in_db: 是否在数据库中
            
        Returns:
            Dict[str, Any]: 统一格式的任务数据对象
        """
        return {
            'id': f"fetch_{stock_id}_adjust_factors",
            'data': {
                'id': stock_id,
                'last_update': last_update,
                'is_in_db': is_in_db
            },
        }

    @staticmethod
    def _calculate_freeze_data_stats(freeze_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算冻结期数据的统计信息
        
        Args:
            freeze_data: 冻结期数据列表
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        if not freeze_data:
            return {}
        
        prices = [float(record.get('close', 0)) for record in freeze_data if record.get('close')]
        if not prices:
            return {}
        
        return {
            'min': min(prices),
            'max': max(prices),
            'avg': sum(prices) / len(prices),
            'count': len(prices)
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