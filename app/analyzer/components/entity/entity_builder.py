#!/usr/bin/env python3
"""
Analyzer-level Entity Builder

Shared constructors and summarizers for opportunity, investment, settled investment,
stock summary, and session summary. Exposed as static methods on EntityBuilder.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from app.analyzer.components.enum.common_enum import InvestmentResult
from app.analyzer.analyzer_service import AnalyzerService


class EntityBuilder:
    @staticmethod
    def to_opportunity(
        stock: Dict[str, Any],
        date: str,
        price: float,
        lower_bound: Optional[float] = None,
        upper_bound: Optional[float] = None,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Construct a standard opportunity entity.

        Required fields: stock{id[,name?]}, date, price
        Optional fields: lower_bound, upper_bound, and extra (strategy-specific)
        """
        opportunity: Dict[str, Any] = {
            'stock': stock or {},
            'date': date,
            'price': price,
        }
        if lower_bound is not None:
            opportunity['lower_bound'] = lower_bound
        if upper_bound is not None:
            opportunity['upper_bound'] = upper_bound

        opportunity['extra_fields'] = extra_fields

        return opportunity

        # merged_extra = extra_fields if isinstance(extra_fields, dict) else extra_fields
        # return EntityBuilder._merge_extra_fields(opportunity, merged_extra)


    # @staticmethod
    # def to_investment(
    #     stock: Dict[str, Any],
    #     start_date: str,
    #     purchase_price: float,
    #     targets: Optional[Dict[str, Any]] = None,
    #     extra: Optional[Dict[str, Any]] = None,
    #     extra_fields: Optional[Dict[str, Any]] = None,
    # ) -> Dict[str, Any]:
    #     """Construct a standard investment entity (unsettled/base)."""
    #     entity: Dict[str, Any] = {
    #         'stock': stock or {},
    #         'start_date': start_date,
    #         'purchase_price': purchase_price,
    #         'targets': EntityBuilder._ensure_targets_schema(targets),
    #     }
    #     merged_extra = extra if isinstance(extra, dict) else extra_fields
    #     return EntityBuilder._merge_extra_fields(entity, merged_extra)


    # @staticmethod
    # def to_settled_investment(
    #     investment: Dict[str, Any],
    #     end_date: str,
    #     result: Any,
    #     extra_fields: Optional[Dict[str, Any]] = None,
    # ) -> Dict[str, Any]:
    #     """Construct a standard settled investment entity."""
    #     result_value = getattr(result, 'value', result)

    #     purchase_price = float(investment.get('purchase_price') or 0.0)
    #     targets = EntityBuilder._ensure_targets_schema(investment.get('targets'))
    #     completed = targets.get('completed') or []

    #     overall_profit = 0.0
    #     for stage in completed:
    #         if isinstance(stage, dict):
    #             if 'weighted_profit' in stage and isinstance(stage['weighted_profit'], (int, float)):
    #                 overall_profit += float(stage['weighted_profit'])
    #             elif 'profit' in stage:
    #                 profit = float(stage.get('profit') or 0.0)
    #                 if 'profit_contribution' in stage:
    #                     overall_profit += profit * float(stage.get('profit_contribution') or 0.0)
    #                 elif 'sell_ratio' in stage:
    #                     overall_profit += profit * float(stage.get('sell_ratio') or 0.0)

    #     overall_profit_rate = AnalyzerService.to_ratio(overall_profit, purchase_price, 2)

    #     invest_duration_days = AnalyzerService.get_duration_in_days(investment.get('start_date'), end_date)

    #     base = {
    #         'stock': investment.get('stock', {}),
    #         'start_date': investment.get('start_date'),
    #         'purchase_price': purchase_price,
    #         'targets': targets,
    #     }
    #     if 'tracking' in investment:
    #         base['tracking'] = investment['tracking']

    #     settled = {
    #         **base,
    #         'result': result_value,
    #         'end_date': end_date,
    #         'overall_profit': overall_profit,
    #         'overall_profit_rate': overall_profit_rate,
    #         'invest_duration_days': invest_duration_days,
    #     }
    #     return EntityBuilder._merge_extra_fields(settled, extra_fields)


    @staticmethod
    def to_stock_summary(
        stock_id: str,
        summary_core: Dict[str, Any],
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        summary: Dict[str, Any] = dict(summary_core or {})
        summary = EntityBuilder._merge_extra_fields(summary, extra_fields)
        return {
            'stock_id': stock_id,
            'summary': summary,
        }


    @staticmethod
    def to_session_summary(
        summary_core: Dict[str, Any],
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        summary: Dict[str, Any] = dict(summary_core or {})
        investments = summary.get('investments', [])
        summary_core_calc = EntityBuilder.compute_stock_summary_core(investments)
        return EntityBuilder._merge_extra_fields(summary_core_calc, extra_fields)


# ========================================================
# Helper methods:
# ========================================================

    @staticmethod
    def _merge_extra_fields(base: Dict[str, Any], extra_fields: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if extra_fields and isinstance(extra_fields, dict):
            for k, v in extra_fields.items():
                if k not in base:
                    base[k] = v
        return base


    @staticmethod
    def _ensure_targets_schema(targets: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        normalized = targets.copy() if isinstance(targets, dict) else {}
        completed = normalized.get('completed')
        if not isinstance(completed, list):
            normalized['completed'] = []
        return normalized


# ========================================================
# Summary calculators (centralized here as requested)
# ========================================================

    @staticmethod
    def compute_stock_summary_core(investments: List[Dict[str, Any]]) -> Dict[str, Any]:
        total_investments = 0
        win_count = 0
        loss_count = 0
        open_count = 0

        total_duration = 0.0
        total_roi = 0.0
        total_profit = 0.0
        total_annual_return = 0.0

        green_dot_count = 0
        yellow_dot_count = 0
        orange_dot_count = 0
        red_dot_count = 0

        for inv in investments or []:
            total_investments += 1

            purchase_price = float(inv.get('purchase_price') or 0.0)
            profit = float(inv.get('overall_profit') or 0.0)
            duration = float(inv.get('invest_duration_days') or 0.0)
            profit_rate = float(inv.get('overall_profit_rate') or 0.0) * 100.0

            total_profit += profit
            total_duration += duration
            if purchase_price > 0:
                total_roi += AnalyzerService.to_ratio(purchase_price + profit, purchase_price) - 1

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

            if duration > 0:
                total_annual_return += (inv.get('overall_profit_rate') or 0.0) * 365.0 / duration

        settled_investments = win_count + loss_count
        win_rate = AnalyzerService.to_ratio(win_count, settled_investments, 4) if settled_investments > 0 else 0.0
        avg_duration_days = AnalyzerService.to_ratio(total_duration, total_investments) if total_investments > 0 else 0.0
        avg_roi = AnalyzerService.to_ratio(total_roi, total_investments) if total_investments > 0 else 0.0
        avg_annual_return = AnalyzerService.to_ratio(total_annual_return, total_investments) if total_investments > 0 else 0.0
        avg_profit_per_investment = AnalyzerService.to_ratio(total_profit, total_investments) if total_investments > 0 else 0.0

        return {
            'total_investments': total_investments,
            'win_count': win_count,
            'loss_count': loss_count,
            'open_count': open_count,
            'settled_investments': settled_investments,
            'win_rate': round(win_rate, 2),
            'avg_duration_days': round(avg_duration_days, 1),
            'avg_roi': round(avg_roi, 4),
            'avg_annual_return': round(avg_annual_return, 4),
            'total_profit': round(total_profit, 2),
            'avg_profit_per_investment': round(avg_profit_per_investment, 2),
            'green_dot_count': green_dot_count,
            'yellow_dot_count': yellow_dot_count,
            'orange_dot_count': orange_dot_count,
            'red_dot_count': red_dot_count,
            'green_dot_rate': AnalyzerService.to_ratio(green_dot_count, total_investments, 4) if total_investments > 0 else 0.0,
            'yellow_dot_rate': AnalyzerService.to_ratio(yellow_dot_count, total_investments, 4) if total_investments > 0 else 0.0,
            'orange_dot_rate': AnalyzerService.to_ratio(orange_dot_count, total_investments, 4) if total_investments > 0 else 0.0,
            'red_dot_rate': AnalyzerService.to_ratio(red_dot_count, total_investments, 4) if total_investments > 0 else 0.0,
            'summary_generated_at': datetime.now().isoformat(),
        }


    @staticmethod
    def compute_session_summary_core(session_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        total_investments = 0
        win_count = 0
        loss_count = 0
        open_count = 0
        green_dot_count = 0
        yellow_dot_count = 0
        orange_dot_count = 0
        red_dot_count = 0
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
                purchase_price = float(inv.get('purchase_price') or 0.0)
                profit = float(inv.get('overall_profit') or 0.0)
                duration = float(inv.get('invest_duration_days') or 0.0)
                profit_rate = float(inv.get('overall_profit_rate') or 0.0) * 100.0

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
        win_rate = (win_count / settled_investments * 100.0) if settled_investments > 0 else 0.0
        annual_return = AnalyzerService.get_annual_return(avg_roi, int(avg_duration_days)) if avg_roi != 0 and avg_duration_days > 0 else 0.0
        avg_profit_per_investment = (total_profit / total_investments) if total_investments > 0 else 0.0

        return {
            'total_investments': total_investments,
            'win_count': win_count,
            'loss_count': loss_count,
            'open_count': open_count,
            'settled_investments': settled_investments,
            'win_rate': round(win_rate, 2),
            'avg_duration_days': round(avg_duration_days, 1),
            'avg_roi': round(avg_roi, 4),
            'annual_return': round(annual_return, 4),
            'avg_annual_return': round(annual_return, 4),
            'total_profit': round(total_profit, 2),
            'avg_profit_per_investment': round(avg_profit_per_investment, 2),
            'total_stocks_with_opportunities': total_stocks_with_opportunities,
            'green_dot_count': green_dot_count,
            'yellow_dot_count': yellow_dot_count,
            'orange_dot_count': orange_dot_count,
            'red_dot_count': red_dot_count,
            'green_dot_rate': AnalyzerService.to_ratio(green_dot_count, total_investments, 4) if total_investments > 0 else 0.0,
            'yellow_dot_rate': AnalyzerService.to_ratio(yellow_dot_count, total_investments, 4) if total_investments > 0 else 0.0,
            'orange_dot_rate': AnalyzerService.to_ratio(orange_dot_count, total_investments, 4) if total_investments > 0 else 0.0,
            'red_dot_rate': AnalyzerService.to_ratio(red_dot_count, total_investments, 4) if total_investments > 0 else 0.0,
            'summary_generated_at': datetime.now().isoformat(),
        }


    @staticmethod
    def to_stock_summary_from_investments(
        stock_id: str,
        investments: List[Dict[str, Any]],
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        core = EntityBuilder.compute_stock_summary_core(investments)
        return EntityBuilder.to_stock_summary(stock_id, core, extra)


    @staticmethod
    def to_session_summary_from_results(
        session_results: List[Dict[str, Any]],
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        core = EntityBuilder.compute_session_summary_core(session_results)
        return EntityBuilder.to_session_summary(core, extra)
