#!/usr/bin/env python3
"""资金模拟报告数据类。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from core.modules.strategy.components.simulator.base.report_base import ReportBase


@dataclass
class CapitalReport(ReportBase):
    initial_capital: float
    final_cash_balance: float
    final_total_equity: float
    final_equity: float
    total_return: float
    max_drawdown: float
    total_trades: int
    buy_trades: int
    sell_trades: int
    win_trades: int
    loss_trades: int
    win_rate: float
    total_profit: float
    avg_pnl_per_trade: float
    total_opportunities: int
    completed_opportunities: int
    unfinished_opportunities: int
    completion_rate: float
    stock_summary: Dict[str, Any]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CapitalReport":
        final_total_equity = float(
            data.get("final_total_equity", data.get("final_equity", 0.0)) or 0.0
        )
        sell_trades = int(data.get("sell_trades", 0) or 0)
        total_profit = float(data.get("total_profit", 0.0) or 0.0)
        avg_pnl = float(data.get("avg_pnl_per_trade", 0.0) or 0.0)
        if avg_pnl == 0.0 and sell_trades > 0:
            avg_pnl = total_profit / sell_trades

        return cls(
            initial_capital=float(data.get("initial_capital", 0.0) or 0.0),
            final_cash_balance=float(data.get("final_cash_balance", 0.0) or 0.0),
            final_total_equity=final_total_equity,
            final_equity=final_total_equity,
            total_return=float(data.get("total_return", 0.0) or 0.0),
            max_drawdown=float(data.get("max_drawdown", 0.0) or 0.0),
            total_trades=int(data.get("total_trades", 0) or 0),
            buy_trades=int(data.get("buy_trades", 0) or 0),
            sell_trades=sell_trades,
            win_trades=int(data.get("win_trades", 0) or 0),
            loss_trades=int(data.get("loss_trades", 0) or 0),
            win_rate=float(data.get("win_rate", 0.0) or 0.0),
            total_profit=total_profit,
            avg_pnl_per_trade=avg_pnl,
            total_opportunities=int(data.get("total_opportunities", 0) or 0),
            completed_opportunities=int(data.get("completed_opportunities", 0) or 0),
            unfinished_opportunities=int(data.get("unfinished_opportunities", 0) or 0),
            completion_rate=float(data.get("completion_rate", 0.0) or 0.0),
            stock_summary=data.get("stock_summary", {}) or {},
        )

    def to_console_lines(self) -> List[str]:
        return [
            f"初始资金: {self.initial_capital:,.2f}",
            f"最终总资产: {self.final_total_equity:,.2f}",
            f"总收益率: {self.total_return * 100:.2f}%",
            f"最大回撤: {self.max_drawdown * 100:.2f}%",
            f"总交易次数: {self.total_trades} (买入: {self.buy_trades}, 卖出: {self.sell_trades})",
            f"盈利/亏损交易: {self.win_trades}/{self.loss_trades}",
            f"交易胜率: {self.win_rate * 100:.2f}%",
            f"总盈亏: {self.total_profit:,.2f}",
            f"单笔平均盈亏: {self.avg_pnl_per_trade:,.2f}",
            f"机会完成/未完成: {self.completed_opportunities}/{self.unfinished_opportunities}",
            f"机会完成率: {self.completion_rate * 100:.2f}%",
        ]

