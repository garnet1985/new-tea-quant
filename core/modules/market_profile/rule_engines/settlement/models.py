#!/usr/bin/env python3
"""settlement Compiled：T+N 卖出约束（如 A 股 T+1）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from core.utils.date.date_utils import DateUtils

from ..shared.base import CompiledRuleBase


@dataclass(frozen=True)
class SettlementCompiled(CompiledRuleBase):
    """``t_plus``：买入后须经过的交易日数才可卖出（0 = T+0 当日可卖，1 = T+1）。"""

    t_plus: int = 0

    def resolve(self, stock_id: str) -> int:
        _ = stock_id
        return self.t_plus

    def sell_blocked_on_date(
        self,
        *,
        buy_date: str,
        trade_date: str,
        backtest_calendar: Optional[Any] = None,
    ) -> bool:
        if self.t_plus <= 0:
            return False
        buy = DateUtils.normalize_str(str(buy_date or ""))
        trade = DateUtils.normalize_str(str(trade_date or ""))
        if not buy or not trade:
            return False

        from core.modules.strategy.engines.shared.helpers.backtest_calendar_context import (
            BacktestCalendarContext,
        )

        ctx = (
            backtest_calendar
            if isinstance(backtest_calendar, BacktestCalendarContext)
            else BacktestCalendarContext.from_dict(backtest_calendar)
        )
        if ctx is not None:
            held_open_days = ctx.count_open_days_between(buy, trade)
            return held_open_days <= self.t_plus

        # 无交易日历时退化为自然日间隔（同日 = 0 天）
        elapsed = DateUtils.diff_days(buy, trade)
        try:
            gap = int(elapsed)
        except (TypeError, ValueError):
            gap = 0
        return gap < self.t_plus


__all__ = ["SettlementCompiled"]
