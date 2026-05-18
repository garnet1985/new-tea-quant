#!/usr/bin/env python3
"""资金不足时的开仓股数决策。"""

from __future__ import annotations

from typing import Optional

from core.modules.strategy.engines.simulator.capital_allocation.data_classes.account import Account
from core.modules.strategy.engines.simulator.capital_allocation.helpers.fees import FeeCalculator


def buy_total_cost(
    shares: int,
    buy_price: float,
    *,
    fee_calculator: Optional[FeeCalculator],
) -> float:
    if shares <= 0 or buy_price <= 0:
        return 0.0
    gross = shares * buy_price
    if fee_calculator is not None:
        return fee_calculator.calculate_total_cost(gross, "buy")
    return gross


def max_affordable_shares(
    available_cash: float,
    buy_price: float,
    *,
    fee_calculator: Optional[FeeCalculator],
) -> int:
    if available_cash <= 0 or buy_price <= 0:
        return 0
    if fee_calculator is not None:
        rate = float(fee_calculator.commission_rate or 0.0)
        denom = buy_price * (1.0 + rate)
        return int(available_cash / denom) if denom > 0 else 0
    return int(available_cash / buy_price)


def resolve_shares_when_insufficient(
    *,
    planned_shares: int,
    min_lot_shares: int,
    account: Account,
    buy_price: float,
    skip_trade_when_insufficient: bool,
    fee_calculator: Optional[FeeCalculator],
    available_cash: Optional[float] = None,
    floor_shares_fn=None,
) -> int:
    """计划仓位买不起时：``skip_trade_when_insufficient`` 为 True 则不买，否则尽量买（整手向下取整）。"""
    if planned_shares <= 0 or buy_price <= 0:
        return 0
    min_lot_shares = max(int(min_lot_shares), 0)
    if min_lot_shares <= 0:
        return 0

    cash = float(available_cash if available_cash is not None else account.cash)
    if buy_total_cost(min_lot_shares, buy_price, fee_calculator=fee_calculator) > cash:
        return 0
    if buy_total_cost(planned_shares, buy_price, fee_calculator=fee_calculator) <= cash:
        return planned_shares

    if skip_trade_when_insufficient:
        return 0

    cap = max_affordable_shares(cash, buy_price, fee_calculator=fee_calculator)
    if floor_shares_fn is not None:
        return int(floor_shares_fn(cap))
    return max(cap, 0)


__all__ = [
    "buy_total_cost",
    "max_affordable_shares",
    "resolve_shares_when_insufficient",
]
