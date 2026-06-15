#!/usr/bin/env python3
from core.modules.market_profile import get_market_profile
from core.modules.strategy.engines.shared.helpers.backtest_calendar_context import (
    BacktestCalendarContext,
)


def _calendar() -> BacktestCalendarContext:
    return BacktestCalendarContext(
        market="SSE",
        period_start="20240101",
        period_end="20240131",
        open_dates=("20240102", "20240103", "20240104", "20240108"),
    )


def test_china_a_stock_settlement_t_plus_one():
    profile = get_market_profile("china_a_stock")
    settlement = profile.settlement
    assert settlement is not None
    assert settlement.t_plus == 1
    cal = _calendar()
    assert profile.sell_blocked_by_settlement(
        buy_date="20240103",
        trade_date="20240103",
        backtest_calendar=cal,
    )
    assert not profile.sell_blocked_by_settlement(
        buy_date="20240103",
        trade_date="20240104",
        backtest_calendar=cal,
    )


def test_settlement_t_plus_zero_allows_same_day():
    from core.modules.market_profile.rule_engines.settlement.models import SettlementCompiled

    compiled = SettlementCompiled(t_plus=0)
    assert not compiled.sell_blocked_on_date(
        buy_date="20240103",
        trade_date="20240103",
        backtest_calendar=_calendar(),
    )
