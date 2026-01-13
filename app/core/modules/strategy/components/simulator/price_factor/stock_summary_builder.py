#!/usr/bin/env python3
"""
股票汇总构建模块

负责从 investments 列表构建单股的 summary
"""

from typing import Dict, Any, List
from .helpers import to_ratio, get_annual_return


class StockSummaryBuilder:
    """股票汇总构建器"""

    @staticmethod
    def build_summary(investments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        从 investments 列表构建单股的 summary
        
        Args:
            investments: investment 记录列表
            
        Returns:
            summary 字典
        """
        if not investments:
            return StockSummaryBuilder._empty_summary()

        total_investments = len(investments)
        total_win = 0
        total_loss = 0
        total_open = 0

        total_profit = 0.0
        total_duration = 0.0
        total_roi = 0.0

        profitable_count = 0
        minor_profitable_count = 0
        unprofitable_count = 0
        minor_unprofitable_count = 0

        for investment in investments:
            result = investment.get("result", "")
            total_profit += investment.get("overall_profit", 0.0)
            total_duration += investment.get("duration_in_days", 0)
            roi = investment.get("roi", 0.0)
            total_roi += roi

            if result == "win":
                total_win += 1
            elif result == "loss":
                total_loss += 1
            elif result == "open":
                total_open += 1

            # ROI 分类
            if roi >= 0.2:
                profitable_count += 1
            elif 0 <= roi < 0.2:
                minor_profitable_count += 1
            elif roi < 0 and roi > -0.2:
                minor_unprofitable_count += 1
            else:
                unprofitable_count += 1

        # 计算平均值
        avg_profit = to_ratio(total_profit, total_investments)
        avg_duration_in_days = to_ratio(total_duration, total_investments)
        avg_roi = to_ratio(total_roi, total_investments, decimals=4)

        # 计算年化收益率
        annual_return_raw = get_annual_return(avg_roi, avg_duration_in_days)
        annual_return = (
            float(annual_return_raw.real)
            if isinstance(annual_return_raw, complex)
            else float(annual_return_raw)
            if isinstance(annual_return_raw, (int, float))
            else 0.0
        )
        annual_return_in_trading_days_raw = get_annual_return(
            avg_roi, avg_duration_in_days, is_trading_days=True
        )
        annual_return_in_trading_days = (
            float(annual_return_in_trading_days_raw.real)
            if isinstance(annual_return_in_trading_days_raw, complex)
            else float(annual_return_in_trading_days_raw)
            if isinstance(annual_return_in_trading_days_raw, (int, float))
            else 0.0
        )

        # 计算胜率
        win_rate = to_ratio(
            profitable_count + minor_profitable_count, total_investments, 3
        )

        return {
            "total_investments": total_investments,
            "total_win": total_win,
            "total_loss": total_loss,
            "total_open": total_open,
            "profitable": profitable_count,
            "minor_profitable": minor_profitable_count,
            "unprofitable": unprofitable_count,
            "minor_unprofitable": minor_unprofitable_count,
            "win_rate": round(win_rate, 1),
            "total_profit": round(total_profit, 2),
            "avg_profit": round(avg_profit, 2),
            "avg_duration_in_days": round(avg_duration_in_days, 1),
            "avg_roi": round(avg_roi, 4),
            "annual_return": round(annual_return, 2),
            "annual_return_in_trading_days": round(annual_return_in_trading_days, 2),
        }

    @staticmethod
    def _empty_summary() -> Dict[str, Any]:
        """返回空的 summary 字典"""
        return {
            "total_investments": 0,
            "total_win": 0,
            "total_loss": 0,
            "total_open": 0,
            "profitable": 0,
            "minor_profitable": 0,
            "unprofitable": 0,
            "minor_unprofitable": 0,
            "win_rate": 0.0,
            "total_profit": 0.0,
            "avg_profit": 0.0,
            "avg_duration_in_days": 0.0,
            "avg_roi": 0.0,
            "annual_return": 0.0,
            "annual_return_in_trading_days": 0.0,
        }

