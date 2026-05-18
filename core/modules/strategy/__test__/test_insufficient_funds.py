#!/usr/bin/env python3
from core.modules.strategy.engines.simulator.capital_allocation.data_classes.account import Account
from core.modules.strategy.engines.simulator.capital_allocation.helpers.insufficient_funds import (
    resolve_shares_when_insufficient,
)


def test_skip_when_cannot_afford_min_lot():
    account = Account(initial_cash=100.0, cash=100.0)
    shares = resolve_shares_when_insufficient(
        planned_shares=1000,
        min_lot_shares=100,
        account=account,
        buy_price=10.0,
        skip_trade_when_insufficient=True,
        fee_calculator=None,
    )
    assert shares == 0


def test_buy_affordable_when_planned_too_large():
    account = Account(initial_cash=5_000.0, cash=5_000.0)
    shares = resolve_shares_when_insufficient(
        planned_shares=1000,
        min_lot_shares=100,
        account=account,
        buy_price=10.0,
        skip_trade_when_insufficient=False,
        fee_calculator=None,
    )
    assert shares == 500


def test_skip_when_planned_unaffordable():
    account = Account(initial_cash=5_000.0, cash=5_000.0)
    shares = resolve_shares_when_insufficient(
        planned_shares=1000,
        min_lot_shares=100,
        account=account,
        buy_price=10.0,
        skip_trade_when_insufficient=True,
        fee_calculator=None,
    )
    assert shares == 0
