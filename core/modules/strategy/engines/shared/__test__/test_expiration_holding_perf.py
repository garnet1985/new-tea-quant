"""expiration 持有天数：短路 + 交易日增量。"""
from core.modules.strategy.engines.shared.data_classes.opportunity import Opportunity
from core.modules.strategy.engines.shared.helpers.backtest_calendar_context import (
    BacktestCalendarContext,
    parse_expiration_hold_spec,
)


def _calendar() -> BacktestCalendarContext:
    return BacktestCalendarContext(
        market="SSE",
        period_start="20240101",
        period_end="20240131",
        open_dates=("20240102", "20240103", "20240104", "20240108"),
    )


def test_parse_expiration_hold_spec_short_circuit():
    assert parse_expiration_hold_spec({}) is None
    assert parse_expiration_hold_spec({"expiration": {}}) is None
    assert parse_expiration_hold_spec({"expiration": {"fixed_window_in_days": 0}}) is None
    spec = parse_expiration_hold_spec(
        {"expiration": {"fixed_window_in_days": 5, "is_trading_days": True}}
    )
    assert spec is not None
    assert spec.fixed_window_in_days == 5


def test_trading_holding_days_incremental_along_klines():
    ctx = _calendar()
    opp = Opportunity(
        stock={"id": "000001.SZ"},
        record_of_today={},
        buy_date="20240102",
        buy_price=10.0,
    )
    spec = parse_expiration_hold_spec(
        {"expiration": {"fixed_window_in_days": 10, "is_trading_days": True}}
    )
    assert opp._expiration_holding_days("20240102", spec, backtest_calendar=ctx) == 1
    assert opp._expiration_holding_days("20240103", spec, backtest_calendar=ctx) == 2
    assert opp._expiration_holding_days("20240104", spec, backtest_calendar=ctx) == 3
    # 同日重复调用不重复计数
    assert opp._expiration_holding_days("20240104", spec, backtest_calendar=ctx) == 3


def test_check_targets_skips_holding_when_no_expiration_window():
    opp = Opportunity(
        stock={"id": "000001.SZ"},
        record_of_today={"date": "20240108", "close": 11.0},
        buy_date="20240102",
        buy_price=10.0,
        protect_loss_active=True,
    )
    goal = {"protect_loss": {"ratio": -0.5}}
    from core.modules.strategy.engines.shared.data_classes.strategy_settings.simulation_settings import (
        StrategySimulationSettings,
    )

    sim = StrategySimulationSettings.from_strategy_root({"simulation": {"template": "deterministic"}})
    # 不应因缺少 expiration 而访问日历
    opp.check_targets(
        sim,
        current_kline={"date": "20240108", "close": 9.0},
        goal_config=goal,
        backtest_calendar=_calendar(),
    )
