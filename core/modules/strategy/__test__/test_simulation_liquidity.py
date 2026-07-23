"""simulation.assumption.tradability.liquidity — tick 成交量参与率。"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.force_run

from core.modules.market_profile.core.markets import create_market_rules
from core.modules.strategy.core.engines.portfolio.allocation_strategy import (
    AllocationStrategy,
)
from core.modules.strategy.core.engines.portfolio.data_class import PortfolioEvent
from core.modules.strategy.core.engines.portfolio.fee_calculator import FeeCalculator
from core.modules.strategy.core.engines.portfolio.simulator import PortfolioSimulator
from core.modules.strategy.core.engines.shared.services.strategy_settings import (
    LiquidityConfig,
    StrategySettings,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.portfolio_settings import (
    PortfolioSettings,
)


def _base_simulation(**tradability_overrides):
    tradability = {"liquidity": {"max_participation_rate": 0.1}}
    tradability.update(tradability_overrides)
    return {
        "simulation": {
            "execution": {
                "mode": "entity_based",
                "steps": [
                    "check_settlement",
                    "check_stop_loss",
                    "check_take_profit",
                    "check_expiration",
                ],
            },
            "assumption": {"template": "none", "tradability": tradability},
            "risk_control": {},
        }
    }


def test_liquidity_defaults() -> None:
    settings = StrategySettings.from_dict(_base_simulation())
    settings.apply_defaults()
    liq = settings.simulation.liquidity
    assert liq.max_participation_rate == 0.1
    assert liq.participation_on_exceed == "clip"
    assert settings.simulation.to_dict()["assumption"]["tradability"]["liquidity"] == {
        "max_participation_rate": 0.1,
        "participation_on_exceed": "clip",
    }


def test_liquidity_validate_rejects_bad_rate() -> None:
    settings = StrategySettings.from_dict(
        _base_simulation(liquidity={"max_participation_rate": 1.5})
    )
    report = settings.validate()
    assert not report.is_valid


def test_apply_clip_and_skip() -> None:
    clip = LiquidityConfig(
        max_participation_rate=0.1, participation_on_exceed="clip"
    )
    skip = LiquidityConfig(
        max_participation_rate=0.1, participation_on_exceed="skip"
    )
    floor = lambda n, _eid: (n // 100) * 100

    shares, tag = clip.apply_to_shares(
        5000, tick_volume=10_000, floor_shares_fn=floor, entity_id="600000.SH"
    )
    assert shares == 1000
    assert tag == LiquidityConfig.TAG_CLIPPED

    shares, tag = skip.apply_to_shares(
        5000, tick_volume=10_000, floor_shares_fn=floor, entity_id="600000.SH"
    )
    assert shares == 0
    assert tag == LiquidityConfig.TAG_SKIP

    shares, tag = clip.apply_to_shares(
        5000, tick_volume=None, floor_shares_fn=floor, entity_id="600000.SH"
    )
    assert shares == 5000
    assert tag is None


def _allocation(liquidity: LiquidityConfig) -> AllocationStrategy:
    portfolio = PortfolioSettings(
        raw_settings={
            "portfolio": {
                "initial_capital": 1_000_000,
                "allocation": {
                    "mode": "equal_capital",
                    "max_portfolio_size": 10,
                    "lots_per_trade": 1,
                    "kelly_fraction": 0.5,
                    "skip_trade_when_insufficient": False,
                },
            }
        }
    )
    portfolio.apply_defaults()
    return AllocationStrategy.create(
        portfolio=portfolio,
        market_rules=create_market_rules("china_a_stock"),
        fee_calculator=FeeCalculator(
            commission_rate=0.0,
            min_commission=0.0,
            stamp_duty_rate=0.0,
            transfer_fee_rate=0.0,
        ),
        liquidity=liquidity,
    )


def test_simulator_clips_buy_by_participation() -> None:
    alloc = _allocation(
        LiquidityConfig(max_participation_rate=0.1, participation_on_exceed="clip")
    )
    sim = PortfolioSimulator.create(
        allocation=alloc,
        fee_calculator=alloc.fee_calculator,
        save_equity_curve=False,
    )
    events = [
        PortfolioEvent(
            kind="buy",
            date="20240103",
            entity_id="600000.SH",
            investment_id="1",
            price=10.0,
            bar_volume=20_000,
        ),
        PortfolioEvent(
            kind="sell",
            date="20240110",
            entity_id="600000.SH",
            investment_id="1",
            price=11.0,
            bar_volume=1_000_000,
        ),
    ]
    result = sim.run(events, initial_capital=1_000_000)
    buys = [t for t in result.trades if t.is_buy()]
    assert len(buys) == 1
    assert buys[0].shares == 2000
    assert result.buy_participation_clipped == 1


def test_simulator_skips_buy_when_participation_exceeded() -> None:
    alloc = _allocation(
        LiquidityConfig(max_participation_rate=0.1, participation_on_exceed="skip")
    )
    sim = PortfolioSimulator.create(
        allocation=alloc,
        fee_calculator=alloc.fee_calculator,
        save_equity_curve=False,
    )
    events = [
        PortfolioEvent(
            kind="buy",
            date="20240103",
            entity_id="600000.SH",
            investment_id="1",
            price=10.0,
            bar_volume=20_000,
        ),
    ]
    result = sim.run(events, initial_capital=1_000_000)
    assert result.trades == []
    assert result.buy_participation_skip == 1
    assert result.skipped_buys == 1
