#!/usr/bin/env python3
"""
结果汇总模块

负责将各 Worker 的结果聚合为策略级 summary
"""

from typing import Dict, Any, List
from .helpers import to_ratio, to_percent


class ResultAggregator:
    """结果汇总器"""

    @staticmethod
    def aggregate_results(stock_summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        将各 Worker 的结果聚合为一个策略级 summary。

        复用 legacy 的 summarize_session_by_default_way 思路：
        - 按单股 summary 的 avg_roi 和 avg_duration 做加权
        - 得到会话级 avg_roi / avg_duration，再推导 annual_return 系列
        """
        if not stock_summaries:
            return {}

        total_investments = 0
        total_win = 0
        total_loss = 0
        total_open = 0
        total_profit = 0.0
        total_roi = 0.0
        total_duration_days = 0.0

        stocks_with_opportunities = len(stock_summaries)

        for stock_summary in stock_summaries:
            summary = stock_summary.get("summary", {})
            investment_count = summary.get("total_investments", 0)

            if investment_count > 0:
                total_investments += investment_count
                total_win += summary.get("total_win", 0)
                total_loss += summary.get("total_loss", 0)
                total_open += summary.get("total_open", 0)
                total_profit += summary.get("total_profit", 0.0)

                stock_avg_roi = summary.get("avg_roi", 0.0)
                total_roi += stock_avg_roi * investment_count
                total_duration_days += summary.get("avg_duration_in_days", 0.0) * investment_count

        # 计算整体平均值
        avg_roi = to_ratio(total_roi, total_investments, decimals=4)
        avg_duration_days = to_ratio(total_duration_days, total_investments)

        # 会话级年化收益率：与 StockSummaryBuilder 保持一致，使用线性近似而非极端复利
        # annual_return 的单位保持为“百分比数值”，例如 18.5 表示 18.5%
        if avg_duration_days > 0:
            annual_return = avg_roi * (365.0 / avg_duration_days)
            annual_return_in_trading_days = avg_roi * (250.0 / avg_duration_days)
        else:
            annual_return = 0.0
            annual_return_in_trading_days = 0.0

        win_rate = to_percent(total_win, total_investments)
        avg_investments_per_stock = to_ratio(
            total_investments, stocks_with_opportunities, decimals=2
        )

        session_summary: Dict[str, Any] = {
            "win_rate": win_rate,
            "avg_roi": avg_roi,
            "annual_return": annual_return,
            "annual_return_in_trading_days": annual_return_in_trading_days,
            "avg_duration_in_days": avg_duration_days,
            "total_investments": total_investments,
            "total_open_investments": total_open,
            "total_win_investments": total_win,
            "total_loss_investments": total_loss,
            "total_profit": round(total_profit, 2),
            "avg_profit_per_investment": round(
                to_ratio(total_profit, total_investments, decimals=2), 2
            ),
            "avg_profit_per_stock": round(
                to_ratio(total_profit, stocks_with_opportunities, decimals=2), 2
            ),
            "avg_investments_per_stock": avg_investments_per_stock,
            "stocks_have_opportunities": stocks_with_opportunities,
        }

        return session_summary


