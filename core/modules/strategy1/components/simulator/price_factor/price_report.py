#!/usr/bin/env python3
"""价格回测报告数据类。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from core.modules.strategy.components.simulator.base.report_base import ReportBase


def _safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


@dataclass
class PriceReport(ReportBase):
    win_rate: float
    avg_roi: float
    annual_return: float
    annual_return_in_trading_days: float
    avg_duration_in_days: float
    avg_duration_in_trading_days: float
    total_investments: int
    total_open_investments: int
    total_win_investments: int
    total_loss_investments: int
    total_completed_investments: int
    total_unfinished_investments: int
    completion_rate: float
    total_profit: float
    avg_profit_per_investment: float
    avg_profit_per_stock: float
    avg_investments_per_stock: float
    stocks_have_opportunities: int

    @classmethod
    def from_stock_summaries(cls, stock_summaries: List[Dict[str, Any]]) -> "PriceReport":
        total_investments = 0
        total_win = 0
        total_loss = 0
        total_open = 0
        total_profit = 0.0
        total_roi = 0.0
        total_duration_days = 0.0
        stocks_with_opportunities = len(stock_summaries)

        for stock_summary in stock_summaries:
            summary = stock_summary.get("summary", {}) or {}
            investment_count = int(summary.get("total_investments", 0) or 0)
            if investment_count <= 0:
                continue
            total_investments += investment_count
            total_win += int(summary.get("total_win", 0) or 0)
            total_loss += int(summary.get("total_loss", 0) or 0)
            total_open += int(summary.get("total_open", 0) or 0)
            total_profit += float(summary.get("total_profit", 0.0) or 0.0)
            total_roi += float(summary.get("avg_roi", 0.0) or 0.0) * investment_count
            total_duration_days += float(summary.get("avg_duration_in_days", 0.0) or 0.0) * investment_count

        avg_roi = round(_safe_div(total_roi, total_investments), 4)
        avg_duration_days = _safe_div(total_duration_days, total_investments)
        avg_duration_trading_days = avg_duration_days * (250.0 / 365.0) if avg_duration_days > 0 else 0.0
        annual_return = avg_roi * (365.0 / avg_duration_days) if avg_duration_days > 0 else 0.0
        annual_return_trading = avg_roi * (250.0 / avg_duration_days) if avg_duration_days > 0 else 0.0
        win_rate = round(_safe_div(total_win, total_investments) * 100.0, 1)
        total_completed = total_win + total_loss
        total_unfinished = total_open
        completion_rate = round(_safe_div(total_completed, total_investments), 4)

        return cls(
            win_rate=win_rate,
            avg_roi=avg_roi,
            annual_return=annual_return,
            annual_return_in_trading_days=annual_return_trading,
            avg_duration_in_days=avg_duration_days,
            avg_duration_in_trading_days=round(avg_duration_trading_days, 1),
            total_investments=total_investments,
            total_open_investments=total_open,
            total_win_investments=total_win,
            total_loss_investments=total_loss,
            total_completed_investments=total_completed,
            total_unfinished_investments=total_unfinished,
            completion_rate=completion_rate,
            total_profit=round(total_profit, 2),
            avg_profit_per_investment=round(_safe_div(total_profit, total_investments), 2),
            avg_profit_per_stock=round(_safe_div(total_profit, stocks_with_opportunities), 2),
            avg_investments_per_stock=round(_safe_div(total_investments, stocks_with_opportunities), 2),
            stocks_have_opportunities=stocks_with_opportunities,
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PriceReport":
        return cls(
            win_rate=float(data.get("win_rate", 0.0) or 0.0),
            avg_roi=float(data.get("avg_roi", 0.0) or 0.0),
            annual_return=float(data.get("annual_return", 0.0) or 0.0),
            annual_return_in_trading_days=float(data.get("annual_return_in_trading_days", 0.0) or 0.0),
            avg_duration_in_days=float(data.get("avg_duration_in_days", 0.0) or 0.0),
            avg_duration_in_trading_days=float(data.get("avg_duration_in_trading_days", 0.0) or 0.0),
            total_investments=int(data.get("total_investments", 0) or 0),
            total_open_investments=int(data.get("total_open_investments", 0) or 0),
            total_win_investments=int(data.get("total_win_investments", 0) or 0),
            total_loss_investments=int(data.get("total_loss_investments", 0) or 0),
            total_completed_investments=int(data.get("total_completed_investments", 0) or 0),
            total_unfinished_investments=int(data.get("total_unfinished_investments", 0) or 0),
            completion_rate=float(data.get("completion_rate", 0.0) or 0.0),
            total_profit=float(data.get("total_profit", 0.0) or 0.0),
            avg_profit_per_investment=float(data.get("avg_profit_per_investment", 0.0) or 0.0),
            avg_profit_per_stock=float(data.get("avg_profit_per_stock", 0.0) or 0.0),
            avg_investments_per_stock=float(data.get("avg_investments_per_stock", 0.0) or 0.0),
            stocks_have_opportunities=int(data.get("stocks_have_opportunities", 0) or 0),
        )

    def to_console_lines(self) -> List[str]:
        return [
            f"胜率: {self.win_rate:.1f}%",
            f"平均每笔投资回报率(ROI): {self.avg_roi * 100:.2f}%",
            f"折算后平均每笔投资年化收益率(自然日): {self.annual_return * 100:.2f}%",
            f"折算后平均每笔投资年化收益率(交易日): {self.annual_return_in_trading_days * 100:.2f}%",
            f"平均投资时长: {self.avg_duration_in_days:.1f} 自然日 / {self.avg_duration_in_trading_days:.1f} 交易日",
            f"总投资次数: {self.total_investments}",
            f"成功/失败/未完成: {self.total_win_investments}/{self.total_loss_investments}/{self.total_open_investments}",
            f"完成率: {self.completion_rate * 100:.2f}%",
            f"每笔平均盈利: {self.avg_profit_per_investment:.2f}",
            f"每只股票平均盈利: {self.avg_profit_per_stock:.2f}",
            f"每只股票平均投资次数: {self.avg_investments_per_stock:.2f}",
            f"产生机会的股票数: {self.stocks_have_opportunities}",
        ]

