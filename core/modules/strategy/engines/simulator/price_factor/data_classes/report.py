#!/usr/bin/env python3
"""价格回测报告数据类。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from core.modules.strategy.engines.shared.report_base import ReportBase


def _tone_signed_pct(pct: float) -> str:
    """Float already as percentage points (e.g. 7.04 for 7.04%)."""
    if pct > 0:
        return "🟢"
    if pct < 0:
        return "🔴"
    return "⚪"


def _tone_win_rate(pct: float) -> str:
    if pct >= 55.0:
        return "🟢"
    if pct >= 45.0:
        return "🟡"
    return "🔴"


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

        avg_roi = round(ReportBase.safe_div(total_roi, total_investments), 4)
        avg_duration_days = ReportBase.safe_div(total_duration_days, total_investments)
        avg_duration_trading_days = avg_duration_days * (250.0 / 365.0) if avg_duration_days > 0 else 0.0
        annual_return = avg_roi * (365.0 / avg_duration_days) if avg_duration_days > 0 else 0.0
        annual_return_trading = avg_roi * (250.0 / avg_duration_days) if avg_duration_days > 0 else 0.0
        win_rate = round(ReportBase.safe_div(total_win, total_investments) * 100.0, 1)
        total_completed = total_win + total_loss
        total_unfinished = total_open
        completion_rate = round(ReportBase.safe_div(total_completed, total_investments), 4)

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
            avg_profit_per_investment=round(
                ReportBase.safe_div(total_profit, total_investments), 2
            ),
            avg_profit_per_stock=round(
                ReportBase.safe_div(total_profit, stocks_with_opportunities), 2
            ),
            avg_investments_per_stock=round(
                ReportBase.safe_div(total_investments, stocks_with_opportunities), 2
            ),
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
        wr_icon = _tone_win_rate(self.win_rate)
        roi_pct = self.avg_roi * 100.0
        roi_icon = _tone_signed_pct(roi_pct)
        ann_cal = self.annual_return * 100.0
        ann_td = self.annual_return_in_trading_days * 100.0
        ann_cal_icon = _tone_signed_pct(ann_cal)
        ann_td_icon = _tone_signed_pct(ann_td)
        lines: List[str] = [
            f"{wr_icon} 胜率: {self.win_rate:.1f}%",
            f"{roi_icon} 平均每笔投资回报率(ROI): {roi_pct:.2f}%",
            "折算后平均每笔投资年化收益率:",
            f" - {ann_cal_icon} 按自然日: {ann_cal:.2f}%",
            f" - {ann_td_icon} 按交易日: {ann_td:.2f}%",
            (
                f"🕙 平均投资时长: {self.avg_duration_in_days:.1f} 自然日 / "
                f"{self.avg_duration_in_trading_days:.1f} 交易日(换算)"
            ),
            f"📊 总投资次数: {self.total_investments}",
            f"✅ 成功次数: {self.total_win_investments}",
            f"❌ 失败次数: {self.total_loss_investments}",
            f"🔄 未完成次数: {self.total_open_investments}",
            f"📈 完成率: {self.completion_rate * 100:.2f}%",
            (
                f"📊 每笔平均盈利: {self.avg_profit_per_investment:.2f} "
                "(单位：1股机会的绝对盈亏)"
            ),
            (
                f"💰 每只股票平均盈利: {self.avg_profit_per_stock:.2f} "
                "(单位：1股机会，按有机会的股票数均分)"
            ),
            f"📊 每只股票平均投资次数: {self.avg_investments_per_stock:.2f}",
            f"💰 产生机会的股票数: {self.stocks_have_opportunities}",
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
        """在终端打印价格因子 session 汇总（不用 logging，避免前缀臃肿）。"""
        if not isinstance(summary, dict) or not summary:
            return
        payload = {
            k: v
            for k, v in summary.items()
            if k not in ("output_version", "sim_version")
        }
        report = cls.from_dict(payload)
        label = (strategy_name or "").strip() or "策略"
        sep = "=" * 60
        print(sep)
        print(f"📊 {label} 策略价格因子回测结果")
        print(sep)
        for line in report.to_console_lines():
            print(line)
        ov = summary.get("output_version") if isinstance(summary.get("output_version"), dict) else {}
        sv = summary.get("sim_version") if isinstance(summary.get("sim_version"), dict) else {}
        print("")
        print(
            "📂 枚举输出版本目录: "
            f"{ov.get('version_dir') or '—'}  │  "
            "本次模拟目录: "
            f"{sv.get('version_dir') or '—'} "
            f"(version_id={sv.get('version_id', '')})"
        )
        if used_db_cache:
            print("💾 本次结果来自 Simulator DB 缓存，未新建模拟输出目录。")


__all__ = ["PriceReport"]

