#!/usr/bin/env python3
"""回测 run 级交易日历 context（SSE 等）；供 enum / price / capital 只读共享。"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.modules.market_profile.constants import DEFAULT_PROFILE_ID
from core.modules.strategy.engines.shared.helpers.backtest_date_resolve import (
    BacktestDateRange,
)

# A 股回测日历与 ``sys_trade_calendar.market`` 一致（见 trade_calendar handler）
CALENDAR_MARKET_SSE = "SSE"


def calendar_market_for_profile(market_profile_id: str) -> str:
    """``settings.market_profile`` → 交易日历 ``market`` 列。"""
    _ = str(market_profile_id or "").strip() or DEFAULT_PROFILE_ID
    return CALENDAR_MARKET_SSE


@dataclass(frozen=True)
class BacktestCalendarContext:
    """回测窗内开市日序列（已排序、去重）。"""

    market: str
    period_start: str
    period_end: str
    open_dates: Tuple[str, ...]

    def is_open_date(self, trade_date: str) -> bool:
        """当日是否为开市日（O(log n)）。"""
        d = str(trade_date or "").strip()
        if not d or not self.open_dates:
            return False
        idx = bisect_left(self.open_dates, d)
        return idx < len(self.open_dates) and self.open_dates[idx] == d

    def count_open_days_between(self, start_date: str, end_date: str) -> int:
        """``[start_date, end_date]`` 内开市日个数（含端点若当日开市）。"""
        start = str(start_date or "").strip()
        end = str(end_date or "").strip()
        if not start or not end or not self.open_dates:
            return 0
        if start > end:
            start, end = end, start
        lo = bisect_left(self.open_dates, start)
        hi = bisect_right(self.open_dates, end)
        return max(hi - lo, 0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "market": self.market,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "open_dates": list(self.open_dates),
        }

    @classmethod
    def from_dict(cls, raw: Optional[Dict[str, Any]]) -> Optional["BacktestCalendarContext"]:
        if not isinstance(raw, dict) or not raw:
            return None
        dates_raw = raw.get("open_dates")
        if not isinstance(dates_raw, list) or not dates_raw:
            return None
        open_dates = tuple(
            sorted({str(d).strip() for d in dates_raw if str(d).strip()})
        )
        if not open_dates:
            return None
        return cls(
            market=str(raw.get("market") or CALENDAR_MARKET_SSE).strip() or CALENDAR_MARKET_SSE,
            period_start=str(raw.get("period_start") or open_dates[0]).strip(),
            period_end=str(raw.get("period_end") or open_dates[-1]).strip(),
            open_dates=open_dates,
        )


@dataclass(frozen=True)
class ExpirationHoldSpec:
    """``goal.expiration`` 中参与持有期判断的字段。"""

    fixed_window_in_days: int
    is_trading_days: bool


def parse_expiration_hold_spec(goal_config: Optional[Dict[str, Any]]) -> Optional[ExpirationHoldSpec]:
    """无 ``fixed_window_in_days`` 时不做持有期计算（短路）。"""
    if not isinstance(goal_config, dict):
        return None
    exp = goal_config.get("expiration")
    if not isinstance(exp, dict):
        return None
    try:
        window = int(exp.get("fixed_window_in_days") or 0)
    except (TypeError, ValueError):
        return None
    if window <= 0:
        return None
    return ExpirationHoldSpec(
        fixed_window_in_days=window,
        is_trading_days=bool(exp.get("is_trading_days", True)),
    )


def resolve_holding_days(
    start_date: str,
    end_date: str,
    *,
    expiration_config: Optional[Dict[str, Any]],
    backtest_calendar: Optional[BacktestCalendarContext],
) -> int:
    """
    ``goal.expiration`` 持有天数：``is_trading_days`` 为真时用日历开市日计数，否则自然日。
    """
    start = str(start_date or "").strip()
    end = str(end_date or "").strip()
    if not start or not end:
        return 0

    exp = expiration_config if isinstance(expiration_config, dict) else {}
    use_trading = bool(exp.get("is_trading_days", True))

    if use_trading and backtest_calendar is not None:
        counted = backtest_calendar.count_open_days_between(start, end)
        return max(counted, 0)

    try:
        from datetime import datetime

        start_dt = datetime.strptime(start, "%Y%m%d")
        end_dt = datetime.strptime(end, "%Y%m%d")
        return max((end_dt - start_dt).days, 0)
    except Exception:
        return 0


def build_backtest_calendar_context(
    *,
    data_manager: Any,
    period: BacktestDateRange,
    market_profile_id: str,
) -> BacktestCalendarContext:
    """按回测窗加载开市日列表（一次 / run）。"""
    start = str(period.start_date or "").strip()
    end = str(period.end_date or "").strip()
    if not start or not end:
        raise ValueError("回测 period_start / period_end 不能为空，无法构建交易日历 context")

    market = calendar_market_for_profile(market_profile_id)
    cal_svc = _calendar_service(data_manager)
    if cal_svc is None:
        raise ValueError("DataManager 无 CalendarService，无法构建交易日历 context")

    open_dates_list: List[str] = cal_svc.load_open_dates(
        start,
        end,
        market=market,
    )
    open_dates = tuple(sorted({str(d).strip() for d in open_dates_list if str(d).strip()}))
    if not open_dates:
        raise ValueError(
            f"回测窗 {start}—{end} 在 sys_trade_calendar（market={market}）无开市日，请先 renew trade_calendar"
        )

    return BacktestCalendarContext(
        market=market,
        period_start=start,
        period_end=end,
        open_dates=open_dates,
    )


def _calendar_service(data_manager: Any) -> Any:
    if hasattr(data_manager, "service"):
        return data_manager.service.calendar
    if hasattr(data_manager, "calendar"):
        return data_manager.calendar
    return None


__all__ = [
    "BacktestCalendarContext",
    "CALENDAR_MARKET_SSE",
    "ExpirationHoldSpec",
    "build_backtest_calendar_context",
    "calendar_market_for_profile",
    "parse_expiration_hold_spec",
    "resolve_holding_days",
]
