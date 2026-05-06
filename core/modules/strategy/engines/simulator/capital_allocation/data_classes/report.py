#!/usr/bin/env python3
"""资金模拟报告数据类。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from core.modules.strategy.engines.shared.report_base import ReportBase


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
        ret_icon = "🟢" if self.total_return >= 0 else "🔴"
        pnl_icon = "🟢" if self.total_profit >= 0 else "🔴"
        wr_icon = "🟢" if self.win_rate >= 0.5 else "🟡" if self.win_rate >= 0.4 else "🔴"
        sell_buy_ratio = (
            round(self.sell_trades / self.buy_trades, 2) if self.buy_trades > 0 else 0.0
        )
        lines = [
            f"💵 初始资金: {self.initial_capital:,.2f}",
            f"📊 最终总资产: {self.final_total_equity:,.2f}",
            f"{ret_icon} 总收益率: {self.total_return * 100:.2f}%",
            f"📉 最大回撤: {self.max_drawdown * 100:.2f}%",
            (
                f"🔄 成交笔数: {self.total_trades} "
                f"(开仓买入 {self.buy_trades} / 减仓卖出 {self.sell_trades}"
                + (
                    f"，卖出÷买入≈{sell_buy_ratio}"
                    if self.buy_trades > 0
                    else ""
                )
                + ")"
            ),
            (
                "   └ 每次触发仅记 1 笔买入；每个成交的 target 记 1 笔卖出，"
                "同一机会可多条 target（分批卖），故卖出笔数常多于买入。"
            ),
            f"✅ 盈利交易 / ❌ 亏损交易: {self.win_trades} / {self.loss_trades}",
            f"{wr_icon} 卖出侧胜率: {self.win_rate * 100:.2f}%",
            f"{pnl_icon} 已实现总盈亏: {self.total_profit:,.2f}",
            f"📐 单笔平均盈亏 (卖出): {self.avg_pnl_per_trade:,.2f}",
            (
                f"🎯 机会 (完成/未完成): "
                f"{self.completed_opportunities}/{self.unfinished_opportunities}"
            ),
            f"📈 机会完成率: {self.completion_rate * 100:.2f}%",
        ]
        return lines

    @classmethod
    def present_session_summary(
        cls,
        summary: Dict[str, Any],
        *,
        strategy_name: str = "",
        used_db_cache: bool = False,
    ) -> None:
        """在终端打印资金分配 session 汇总（print，与 PriceReport 一致）。"""
        if not isinstance(summary, dict) or not summary:
            return
        report = cls.from_dict(summary)
        label = (strategy_name or "").strip() or "策略"
        sep = "=" * 60
        print(sep)
        print(f"💰 {label} 策略资金分配回测结果")
        print(sep)
        for line in report.to_console_lines():
            print(line)
        print("")
        if used_db_cache:
            print("💾 本次结果来自 Simulator DB 缓存，未新建模拟输出目录。")


__all__ = ["CapitalReport"]

