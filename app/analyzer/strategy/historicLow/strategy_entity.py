#!/usr/bin/env python3
"""
策略实体生成器 - 集中管理所有entity的生成函数
"""
import pprint
from typing import Dict, List, Any, Tuple
from datetime import datetime

from app.analyzer.strategy.historicLow.strategy_service import HistoricLowService
from app.analyzer.analyzer_service import AnalyzerService
from app.data_source.data_source_service import DataSourceService
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
    def to_stock_summary(stock_simulation_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        从单只股票的模拟结果构造统一的股票级汇总。
        
        Args:
            stock_simulation_result: 股票模拟结果，包含 stock_info 和 investments 列表
            
        Returns:
            Dict[str, Any]: 统一格式的股票汇总对象
        """
        stock_info = stock_simulation_result.get('stock_info', {})
        investments = stock_simulation_result.get('investments', [])

        total_investments = len(investments)
        success_count = len([inv for inv in investments if inv.get('result') == InvestmentResult.WIN.value])
        fail_count = len([inv for inv in investments if inv.get('result') == InvestmentResult.LOSS.value])
        open_count = len([inv for inv in investments if inv.get('result') == InvestmentResult.OPEN.value])

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
        avg_annual_return = AnalyzerService.get_annual_return(total_roi / total_investments, int(avg_duration)) if total_investments > 0 and avg_duration > 0 else 0.0

        import copy

        # 清理投资记录以用于输出保存：
        cleaned_investments = copy.deepcopy(investments)
        for inv in cleaned_investments:
            # 清理 targets 中的无关字段
            if 'targets' in inv:
                inv_targets = inv['targets']
                inv_targets.pop('investment_ratio_left', None)
                inv_targets.pop('all', None)
            # 将 opportunity 简化为 low_point_ref
            if 'opportunity' in inv:
                opp = inv.get('opportunity') or {}
                low_point_ref = opp.get('low_point_ref') or {}
                inv['low_point_ref'] = low_point_ref
                # 移除原 opportunity 字段
                inv.pop('opportunity', None)

        return {
            'stock_info': stock_info,
            'investments': cleaned_investments,
            'summary': {
                'total_investments': total_investments,
                'success_count': success_count,
                'fail_count': fail_count,
                'open_count': open_count,
                'win_rate': round(win_rate, 1),
                'total_profit': round(total_profit, 2),
                'avg_profit': round(avg_profit, 2),
                'avg_duration_days': round(avg_duration, 1),
                'avg_roi': round(avg_roi, 2),
                'avg_annual_return': round(avg_annual_return, 2)
            }
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