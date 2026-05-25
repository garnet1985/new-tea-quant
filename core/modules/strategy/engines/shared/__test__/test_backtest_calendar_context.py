"""交易日历 context 与持有天数。"""
from unittest.mock import MagicMock

from core.modules.strategy.engines.shared.helpers.backtest_calendar_context import (
    BacktestCalendarContext,
    build_backtest_calendar_context,
    resolve_holding_days,
)


def test_count_open_days_between_inclusive():
    ctx = BacktestCalendarContext(
        market="SSE",
        period_start="20240101",
        period_end="20240131",
        open_dates=("20240102", "20240103", "20240104", "20240108"),
    )
    assert ctx.count_open_days_between("20240102", "20240104") == 3
    assert ctx.count_open_days_between("20240105", "20240110") == 1


def test_resolve_holding_days_trading_vs_calendar():
    ctx = BacktestCalendarContext(
        market="SSE",
        period_start="20240101",
        period_end="20240131",
        open_dates=("20240102", "20240103", "20240108"),
    )
    exp_trading = {"fixed_window_in_days": 2, "is_trading_days": True}
    assert (
        resolve_holding_days(
            "20240102",
            "20240108",
            expiration_config=exp_trading,
            backtest_calendar=ctx,
        )
        == 3
    )
    exp_cal = {"fixed_window_in_days": 2, "is_trading_days": False}
    assert (
        resolve_holding_days(
            "20240102",
            "20240108",
            expiration_config=exp_cal,
            backtest_calendar=ctx,
        )
        == 6
    )


def test_build_backtest_calendar_context_loads_open_dates():
    cal_svc = MagicMock()
    cal_svc.load_open_dates.return_value = ["20240102", "20240103"]
    dm = MagicMock()
    dm.service.calendar = cal_svc

    from core.modules.strategy.engines.shared.helpers.backtest_date_resolve import (
        BacktestDateRange,
    )

    ctx = build_backtest_calendar_context(
        data_manager=dm,
        period=BacktestDateRange("20240101", "20240110", "", ""),
        market_profile_id="china_a_stock",
    )
    assert ctx.market == "SSE"
    assert ctx.open_dates == ("20240102", "20240103")
    cal_svc.load_open_dates.assert_called_once_with(
        "20240101", "20240110", market="SSE"
    )
