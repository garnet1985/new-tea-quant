"""Portfolio 第一批 data class 单测。"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.force_run

from core.modules.strategy.core.engines.shared.services.simulation_input.stock_investments import (
    InvestmentRow,
)
from core.modules.strategy.core.engines.portfolio.data_class import (
    Account,
    PortfolioEvent,
    PortfolioInvestment,
    Position,
    Trade,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.portfolio_settings import (
    PortfolioSettings,
)


def test_account_equity_and_open_position_count():
    account = Account(initial_cash=100_000.0, cash=80_000.0)
    account.positions["600000.SH"] = Position(
        entity_id="600000.SH",
        shares=1000,
        average_cost=10.0,
    )
    assert account.has_position("600000.SH")
    assert account.open_position_count() == 1
    assert account.equity({"600000.SH": 12.0}) == 80_000.0 + 12_000.0


def test_portfolio_event_from_investment_row_raw_and_roi_sell():
    row = InvestmentRow(
        investment_id="1",
        entry_date="20240103",
        entry_price=10.0,
        entry_price_raw=20.0,
        exit_date="20240110",
        exit_price=11.0,
        exit_price_raw=22.0,
        weighted_roi=0.1,
        lifecycle="complete",
    )
    events = PortfolioEvent.from_investment_row(row, "600000.SH")
    assert len(events) == 2
    buy, sell = events
    assert buy.is_buy()
    assert buy.price == 20.0
    assert sell.is_sell()
    assert sell.price == 22.0  # 20 * (1 + 0.1)
    assert sell.roi == 0.1


def test_portfolio_event_skips_without_entry_price_raw():
    row = InvestmentRow(
        investment_id="2",
        entry_date="20240103",
        entry_price=10.0,
        entry_price_raw=0.0,
        exit_date="20240110",
        weighted_roi=0.1,
    )
    assert PortfolioEvent.from_investment_row(row, "600000.SH") == []


def test_portfolio_investment_from_trades_profit():
    buy = Trade.make_buy(
        date="20240103",
        entity_id="600000.SH",
        investment_id="1",
        shares=100,
        price=20.0,
        fees=5.0,
    )
    sell = Trade.make_sell(
        date="20240110",
        entity_id="600000.SH",
        investment_id="1",
        shares=100,
        sell_price=22.0,
        buy_price=20.0,
        fees=5.0,
    )
    # share value profit：100*(22-20)=200；fees 不计入 profit
    assert sell.profit == 200.0
    assert sell.net_proceeds == 2195.0
    inv = PortfolioInvestment.from_trades(buy, [sell])
    assert inv.lifecycle == "complete"
    assert inv.shares == 100
    assert inv.realized_profit == 200.0
    assert inv.holding_days == 7
    assert abs(inv.roi - (200.0 / 2005.0)) < 1e-9


def test_trade_share_value_profit_ignores_fees():
    assert Trade.share_value_profit(100, sell_price=22.0, buy_price=20.0) == 200.0
    assert Trade.purchase_share_value(100, 20.0) == 2000.0
    assert Trade.sell_share_value(100, 22.0) == 2200.0


def test_portfolio_settings_defaults_and_validate():
    settings = PortfolioSettings(raw_settings={})
    report = settings.validate()
    assert report.is_valid
    assert settings.initial_capital == 1_000_000.0
    assert settings.allocation.mode == "equal_capital"
    assert settings.output.save_trades is True

    bad = PortfolioSettings(
        raw_settings={"portfolio": {"initial_capital": 100}, "capital_simulator": {}}
    )
    bad_report = bad.validate()
    assert not bad_report.is_valid
    paths = {e["field_path"] for e in bad_report.errors}
    assert "portfolio.initial_capital" in paths
    assert "capital_simulator" in paths
