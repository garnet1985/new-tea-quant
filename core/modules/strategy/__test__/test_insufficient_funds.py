#!/usr/bin/env python3
from core.modules.strategy.engines.simulator.capital_allocation.helpers.allocation import (
    _resolve_shares_when_insufficient,
)


def test_skip_when_cannot_afford_min_lot():
    shares = _resolve_shares_when_insufficient(
        planned_shares=1000,
        min_lot_shares=100,
        cash=100.0,
        buy_price=10.0,
        skip_trade_when_insufficient=True,
        fee_calculator=None,
        floor_shares_fn=lambda x: x,
    )
    assert shares == 0


def test_buy_affordable_when_planned_too_large():
    shares = _resolve_shares_when_insufficient(
        planned_shares=1000,
        min_lot_shares=100,
        cash=5_000.0,
        buy_price=10.0,
        skip_trade_when_insufficient=False,
        fee_calculator=None,
        floor_shares_fn=lambda x: x,
    )
    assert shares == 500


def test_skip_when_planned_unaffordable():
    shares = _resolve_shares_when_insufficient(
        planned_shares=1000,
        min_lot_shares=100,
        cash=5_000.0,
        buy_price=10.0,
        skip_trade_when_insufficient=True,
        fee_calculator=None,
        floor_shares_fn=lambda x: x,
    )
    assert shares == 0
