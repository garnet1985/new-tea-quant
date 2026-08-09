"""PortfolioSimulator / AllocationStrategy / finalize 单测。"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.force_run

from core.modules.market_profile import MarketRulesProxy
from core.modules.strategy.core.engines.portfolio.allocation_strategy import (
    AllocationStrategy,
)
from core.modules.strategy.core.engines.portfolio.data_class import (
    Account,
    PortfolioEvent,
)
from core.modules.strategy.core.engines.portfolio.fee_calculator import FeeCalculator
from core.modules.strategy.core.engines.portfolio.report_manager import (
    ReportManager,
)
from core.modules.strategy.core.engines.portfolio.simulator import PortfolioSimulator
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)


def _strategy_settings(**overrides) -> StrategySettings:
    raw = {
        "portfolio": {
            "initial_capital": 1_000_000,
            "allocation": {
                "mode": "equal_capital",
                "max_portfolio_size": 10,
                "lots_per_trade": 1,
                "kelly_fraction": 0.5,
                "skip_trade_when_insufficient": False,
            },
            "output": {"save_trades": True, "save_equity_curve": True},
        }
    }
    for key, value in overrides.items():
        if key == "allocation":
            raw["portfolio"]["allocation"].update(value)
        else:
            raw["portfolio"][key] = value
    settings = StrategySettings.from_dict(raw)
    settings.apply_defaults()
    return settings


def _allocation(**kwargs) -> AllocationStrategy:
    settings = _strategy_settings(**kwargs)
    return AllocationStrategy.create(
        settings=settings,
        market_rules=MarketRulesProxy.for_market("china_a_stock"),
        fee_calculator=FeeCalculator(
            commission_rate=0.0,
            min_commission=0.0,
            stamp_duty_rate=0.0,
            transfer_fee_rate=0.0,
        ),
    )


def test_equal_capital_buys_per_slot_budget():
    alloc = _allocation(allocation={"max_portfolio_size": 10})
    account = Account(initial_cash=1_000_000, cash=1_000_000)
    # 100_000 / 10 = 10_000 股 → A 股整手 100 → 10000
    shares = alloc.calculate_shares_to_buy(account, buy_price=10.0, entity_id="600000.SH")
    assert shares == 10_000


def test_equal_capital_skips_when_cash_below_slot():
    alloc = _allocation(allocation={"max_portfolio_size": 10})
    account = Account(initial_cash=1_000_000, cash=50_000)
    shares = alloc.calculate_shares_to_buy(account, buy_price=10.0, entity_id="600000.SH")
    assert shares == 0


def test_equal_shares_uses_lots_per_trade():
    alloc = _allocation(
        allocation={"mode": "equal_shares", "lots_per_trade": 2, "max_portfolio_size": 10}
    )
    account = Account(initial_cash=1_000_000, cash=1_000_000)
    shares = alloc.calculate_shares_to_buy(account, buy_price=10.0, entity_id="600000.SH")
    assert shares == 200


def test_simulator_buy_sell_realizes_share_value_profit():
    alloc = _allocation(allocation={"max_portfolio_size": 2})
    fees = FeeCalculator(
        commission_rate=0.0,
        min_commission=0.0,
        stamp_duty_rate=0.0,
        transfer_fee_rate=0.0,
    )
    sim = PortfolioSimulator.create(
        allocation=alloc, fee_calculator=fees, save_equity_curve=True
    )
    events = [
        PortfolioEvent(
            kind="buy",
            date="20240103",
            entity_id="600000.SH",
            investment_id="a",
            price=10.0,
        ),
        PortfolioEvent(
            kind="sell",
            date="20240110",
            entity_id="600000.SH",
            investment_id="a",
            price=11.0,
            roi=0.1,
        ),
    ]
    result = sim.run(events, initial_capital=1_000_000)
    assert result.completed_count == 1
    assert result.win_count == 1
    assert len(result.trades) == 2
    buy, sell = result.trades
    assert buy.is_buy()
    assert sell.is_sell()
    assert buy.shares == 50_000  # 500_000 / 10
    assert sell.profit == pytest.approx(50_000.0)  # 50k * 1
    assert result.account.cash == pytest.approx(1_050_000.0)
    assert result.account.open_position_count() == 0
    assert len(result.equity_curve) >= 1


def test_simulator_same_investment_id_does_not_cross_entity_sell():
    """裸 investment_id 跨股碰撞时，不得用 B 的卖价平 A 的仓。"""
    alloc = _allocation(allocation={"max_portfolio_size": 10})
    fees = FeeCalculator(
        commission_rate=0.0,
        min_commission=0.0,
        stamp_duty_rate=0.0,
        transfer_fee_rate=0.0,
    )
    sim = PortfolioSimulator.create(allocation=alloc, fee_calculator=fees)
    events = [
        PortfolioEvent(
            kind="buy",
            date="20240103",
            entity_id="600000.SH",
            investment_id="1",
            price=10.0,
        ),
        # 另一标的同号 sell：修复前会误平 600000
        PortfolioEvent(
            kind="sell",
            date="20240104",
            entity_id="000001.SZ",
            investment_id="1",
            price=100.0,
            roi=9.0,
        ),
        PortfolioEvent(
            kind="sell",
            date="20240110",
            entity_id="600000.SH",
            investment_id="1",
            price=11.0,
            roi=0.1,
        ),
    ]
    result = sim.run(events, initial_capital=1_000_000)
    assert result.skipped_sells == 1  # 000001 无对应 buy
    assert result.completed_count == 1
    sells = [t for t in result.trades if t.is_sell()]
    assert len(sells) == 1
    assert sells[0].entity_id == "600000.SH"
    assert sells[0].price == pytest.approx(11.0)
    assert sells[0].profit == pytest.approx(result.trades[0].shares * 1.0)


def test_simulator_skips_sell_without_open_lot():
    alloc = _allocation()
    fees = FeeCalculator(
        commission_rate=0.0, min_commission=0.0, stamp_duty_rate=0.0, transfer_fee_rate=0.0
    )
    sim = PortfolioSimulator.create(allocation=alloc, fee_calculator=fees)
    events = [
        PortfolioEvent(
            kind="sell",
            date="20240110",
            entity_id="600000.SH",
            investment_id="ghost",
            price=11.0,
        ),
    ]
    result = sim.run(events, initial_capital=100_000)
    assert result.skipped_sells == 1
    assert result.trades == []


def test_report_manager_finalize_writes_files(tmp_path: Path):
    alloc = _allocation(allocation={"max_portfolio_size": 2})
    fees = FeeCalculator(
        commission_rate=0.0, min_commission=0.0, stamp_duty_rate=0.0, transfer_fee_rate=0.0
    )
    result = PortfolioSimulator.create(allocation=alloc, fee_calculator=fees).run(
        [
            PortfolioEvent(
                kind="buy",
                date="20240103",
                entity_id="600000.SH",
                investment_id="a",
                price=10.0,
            ),
            PortfolioEvent(
                kind="sell",
                date="20240110",
                entity_id="600000.SH",
                investment_id="a",
                price=11.0,
            ),
        ],
        initial_capital=1_000_000,
    )
    report = ReportManager(
        output_dir=tmp_path / "1",
        strategy_key="demo",
        strategy_path="demo/rsi",
        version_id=1,
        enum_version_id="3",
    ).finalize(result, period={"start_date": "20240101", "end_date": "20240131"})
    assert report["success"] is True
    assert report["version_id"] == 1
    assert report["capitalMetrics"]["totalTrades"] >= 2
    assert report["capitalMetrics"]["winTrades"] == 1
    assert len(report["capitalMetrics"]["equityCurveLabels"]) >= 2
    assert (tmp_path / "1" / "trades.json").is_file()
    assert (tmp_path / "1" / "equity_curve.json").is_file()
    assert (tmp_path / "1" / "overall_report.json").is_file()
    assert (tmp_path / "1" / "entity_list.json").is_file()
    assert (tmp_path / "1" / "performance.json").is_file()
    assert report["summary"]["completed_investments"] == 1
    assert report["summary"]["total_return"] == pytest.approx(0.05)
    assert report["summary"]["final_total_equity"] == pytest.approx(1_050_000.0)
