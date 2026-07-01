#!/usr/bin/env python3
"""涨跌停跳过：tradability 辅助、资金回放、价格报告聚合。"""

# 单独跑本文件时需先拉齐 strategy 依赖图，避免 capital_allocation_flow_impl 循环导入。
from core.modules.strategy.engines.shared.data_classes.strategy_settings.strategy_settings import (  # noqa: F401
    StrategySettings,
)

from core.modules.market_profile import clear_market_profile_cache, get_market_profile
from core.modules.strategy.engines.simulator.capital_allocation.data_classes.account import (
    Account,
    Position,
)
from core.modules.strategy.engines.simulator.capital_allocation.data_classes.report import (
    CapitalReport,
)
from core.modules.strategy.engines.simulator.capital_allocation.helpers.allocation import (
    AllocationStrategy,
)
from core.modules.strategy.engines.simulator.price_factor.data_classes.report import (
    PriceReport,
)
from core.modules.strategy.engines.shared.helpers.tradability import (
    should_skip_buy,
    should_skip_sell,
)
from core.modules.strategy.services.data.output import SimulationEvent


def setup_function():
    clear_market_profile_cache()


def teardown_function():
    clear_market_profile_cache()


def test_should_skip_buy_and_sell_at_limit():
    profile = get_market_profile("china_a_stock")
    limit_up, limit_down = profile.compute_limit_prices("000001.SZ", 10.0)

    buy_row = {"buy_prev_close": 10.0}
    assert should_skip_buy(
        buy_row, profile, "000001.SZ", limit_up, allow_at_limit=False
    )
    assert not should_skip_buy(
        buy_row, profile, "000001.SZ", limit_up, allow_at_limit=True
    )
    assert not should_skip_buy(
        {**buy_row, "buy_at_limit_up": False},
        profile,
        "000001.SZ",
        limit_up,
        allow_at_limit=False,
    )

    sell_row = {"sell_prev_close": 10.0}
    assert should_skip_sell(
        sell_row, profile, "000001.SZ", limit_down, allow_at_limit=False
    )
    assert not should_skip_sell(
        sell_row, profile, "000001.SZ", limit_down, allow_at_limit=True
    )


def test_capital_trigger_skips_buy_at_limit_up():
    from core.modules.strategy.engines.simulator.capital_allocation.capital_allocation_flow_impl import (
        CapitalAllocationFlowImpl,
    )

    profile = get_market_profile("china_a_stock")
    limit_up, _ = profile.compute_limit_prices("000001.SZ", 10.0)
    impl = CapitalAllocationFlowImpl()
    account = Account(initial_cash=1_000_000.0, cash=1_000_000.0)
    allocation = AllocationStrategy(
        mode="equal_capital",
        initial_capital=1_000_000.0,
        max_portfolio_size=10,
        market_profile=profile,
        allow_buy_at_limit_up=False,
    )
    skips = {"buy_at_limit_up": 0, "sell_at_limit_down": 0}
    event = SimulationEvent(
        event_type="trigger",
        date="20240103",
        stock_id="000001.SZ",
        opportunity_id="opp1",
        opportunity={
            "opportunity_id": "opp1",
            "buy_date": "20240103",
            "buy_price": limit_up,
            "buy_at_limit_up": True,
            "buy_prev_close": 10.0,
        },
    )
    trade = impl._handle_trigger_event(
        event,
        account,
        allocation,
        {},
        tradability_skips=skips,
    )
    assert trade is None
    assert skips["buy_at_limit_up"] == 1
    assert account.cash == 1_000_000.0


def test_capital_trigger_buys_when_buy_bar_volume_missing():
    from core.modules.strategy.engines.simulator.capital_allocation.capital_allocation_flow_impl import (
        CapitalAllocationFlowImpl,
    )

    from core.modules.strategy.engines.simulator.capital_allocation.helpers.fees import (
        FeeCalculator,
    )

    profile = get_market_profile("china_a_stock")
    impl = CapitalAllocationFlowImpl()
    account = Account(initial_cash=1_000_000.0, cash=1_000_000.0)
    allocation = AllocationStrategy(
        mode="equal_capital",
        initial_capital=1_000_000.0,
        max_portfolio_size=10,
        market_profile=profile,
        fee_calculator=FeeCalculator(
            commission_rate=0.00025,
            min_commission=5.0,
            stamp_duty_rate=0.001,
            transfer_fee_rate=0.0,
        ),
        max_participation_rate=0.1,
        participation_on_exceed="skip",
    )
    event = SimulationEvent(
        event_type="trigger",
        date="20240103",
        stock_id="000001.SZ",
        opportunity_id="opp1",
        opportunity={
            "opportunity_id": "opp1",
            "buy_date": "20240103",
            "buy_price": 10.0,
            "buy_at_limit_up": False,
            "buy_prev_close": 10.0,
        },
    )
    trade = impl._handle_trigger_event(event, account, allocation, {})
    assert trade is not None
    assert trade["side"] == "buy"
    assert trade["shares"] > 0
    assert account.cash < 1_000_000.0


def test_capital_target_skips_sell_at_limit_down():
    from core.modules.strategy.engines.simulator.capital_allocation.capital_allocation_flow_impl import (
        CapitalAllocationFlowImpl,
    )

    profile = get_market_profile("china_a_stock")
    _, limit_down = profile.compute_limit_prices("000001.SZ", 10.0)
    impl = CapitalAllocationFlowImpl()
    account = Account(initial_cash=0.0, cash=0.0)
    account.positions["000001.SZ"] = Position(
        stock_id="000001.SZ",
        shares=100,
        avg_cost=10.0,
        current_opportunity_id="opp1",
    )
    allocation = AllocationStrategy(
        mode="equal_capital",
        initial_capital=1_000_000.0,
        max_portfolio_size=10,
        market_profile=profile,
        allow_sell_at_limit_down=False,
    )
    skips = {"buy_at_limit_up": 0, "sell_at_limit_down": 0}
    event = SimulationEvent(
        event_type="target",
        date="20240104",
        stock_id="000001.SZ",
        opportunity_id="opp1",
        target={
            "opportunity_id": "opp1",
            "sell_price": limit_down,
            "sell_at_limit_down": True,
            "sell_prev_close": 10.0,
            "sell_ratio": 1.0,
        },
    )
    trade = impl._handle_target_event(
        event,
        account,
        allocation.fee_calculator,
        allocation,
        completed_opportunities_map={},
        tradability_skips=skips,
    )
    assert trade is None
    assert skips["sell_at_limit_down"] == 1
    assert account.positions["000001.SZ"].shares == 100


def test_build_summary_includes_tradability_skips():
    from core.modules.strategy.engines.simulator.capital_allocation.capital_allocation_flow_impl import (
        CapitalAllocationFlowImpl,
    )

    impl = CapitalAllocationFlowImpl()
    account = Account(initial_cash=100_000.0, cash=100_000.0)
    summary = impl.build_summary(
        account=account,
        trades=[],
        equity_curve=[{"total_equity": 100_000.0}],
        initial_capital=100_000.0,
        events=[],
        completed_opportunities_map={},
        tradability_skips={"buy_at_limit_up": 3, "sell_at_limit_down": 2},
    )
    assert summary["skipped_buy_at_limit_up"] == 3
    assert summary["skipped_sell_at_limit_down"] == 2


def test_price_report_aggregates_tradability_skips():
    stock_summaries = [
        {
            "skipped_buy_at_limit_up": 2,
            "skipped_sell_at_limit_down": 1,
            "summary": {"total_investments": 0},
        },
        {
            "skipped_buy_at_limit_up": 1,
            "skipped_sell_at_limit_down": 0,
            "summary": {
                "total_investments": 1,
                "total_win": 1,
                "total_loss": 0,
                "total_open": 0,
                "total_profit": 100.0,
                "avg_roi": 0.1,
                "avg_duration_in_days": 5.0,
            },
        },
    ]
    report = PriceReport.from_stock_summaries(stock_summaries)
    assert report.skipped_buy_at_limit_up == 3
    assert report.skipped_sell_at_limit_down == 1


def test_capital_report_from_dict_includes_skips():
    report = CapitalReport.from_dict(
        {
            "initial_capital": 100_000.0,
            "final_equity": 100_000.0,
            "total_return": 0.0,
            "max_drawdown": 0.0,
            "total_trades": 0,
            "buy_trades": 0,
            "sell_trades": 0,
            "win_trades": 0,
            "loss_trades": 0,
            "win_rate": 0.0,
            "total_profit": 0.0,
            "avg_profit_per_trade": 0.0,
            "completion_rate": 0.0,
            "stock_summary": {},
            "skipped_buy_at_limit_up": 4,
            "skipped_sell_at_limit_down": 2,
        }
    )
    assert report.skipped_buy_at_limit_up == 4
    assert report.skipped_sell_at_limit_down == 2
