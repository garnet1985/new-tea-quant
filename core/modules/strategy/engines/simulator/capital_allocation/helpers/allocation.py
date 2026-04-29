#!/usr/bin/env python3
from typing import Optional, Literal

from core.modules.strategy.engines.simulator.capital_allocation.data_classes.account import Account
from .fees import FeeCalculator


class AllocationStrategy:
    def __init__(
        self,
        mode: Literal["equal_capital", "equal_shares", "kelly"],
        initial_capital: float,
        max_portfolio_size: int,
        lot_size: int = 100,
        lots_per_trade: int = 1,
        kelly_fraction: float = 0.5,
        fee_calculator: Optional[FeeCalculator] = None,
    ):
        self.mode = mode
        self.initial_capital = initial_capital
        self.max_portfolio_size = max_portfolio_size
        self.lot_size = lot_size
        self.lots_per_trade = lots_per_trade
        self.kelly_fraction = kelly_fraction
        self.fee_calculator = fee_calculator
        self.per_trade_capital = initial_capital / max_portfolio_size

    def calculate_shares_to_buy(
        self, account: Account, trigger_price: float, win_rate: Optional[float] = None
    ) -> int:
        if self.mode == "equal_capital":
            return self._calculate_equal_capital(account, trigger_price)
        if self.mode == "equal_shares":
            return self._calculate_equal_shares(account, trigger_price)
        if self.mode == "kelly":
            return self._calculate_kelly(account, trigger_price, win_rate)
        return 0

    def _calculate_equal_capital(self, account: Account, trigger_price: float) -> int:
        if account.cash < self.per_trade_capital:
            return 0
        max_shares = int(self.per_trade_capital / trigger_price)
        buy_shares = (max_shares // self.lot_size) * self.lot_size
        if buy_shares == 0:
            return 0
        gross_amount = buy_shares * trigger_price
        total_cost = (
            self.fee_calculator.calculate_total_cost(gross_amount, "buy")
            if self.fee_calculator
            else gross_amount
        )
        if account.cash < total_cost:
            available_capital = min(account.cash, self.per_trade_capital)
            max_affordable_shares = int(
                (available_capital / (trigger_price * (1 + self.fee_calculator.commission_rate)))
                if self.fee_calculator
                else (available_capital / trigger_price)
            )
            buy_shares = (max_affordable_shares // self.lot_size) * self.lot_size
        return buy_shares

    def _calculate_equal_shares(self, account: Account, trigger_price: float) -> int:
        target_shares = self.lot_size * self.lots_per_trade
        gross_amount = target_shares * trigger_price
        total_cost = (
            self.fee_calculator.calculate_total_cost(gross_amount, "buy")
            if self.fee_calculator
            else gross_amount
        )
        return target_shares if account.cash >= total_cost else 0

    def _calculate_kelly(
        self, account: Account, trigger_price: float, win_rate: Optional[float] = None
    ) -> int:
        if win_rate is None:
            return 0
        f_raw = 2 * win_rate - 1
        if f_raw <= 0:
            return 0
        kelly_divisor = 1.0 / self.kelly_fraction if self.kelly_fraction > 0 else 1.0
        target_capital = (f_raw / kelly_divisor) * account.cash
        buy_shares = (int(target_capital / trigger_price) // self.lot_size) * self.lot_size
        if buy_shares == 0:
            return 0
        gross_amount = buy_shares * trigger_price
        total_cost = (
            self.fee_calculator.calculate_total_cost(gross_amount, "buy")
            if self.fee_calculator
            else gross_amount
        )
        if account.cash < total_cost:
            max_affordable = int(
                (account.cash / (trigger_price * (1 + self.fee_calculator.commission_rate)))
                if self.fee_calculator
                else (account.cash / trigger_price)
            )
            buy_shares = (max_affordable // self.lot_size) * self.lot_size
        return buy_shares


__all__ = ["AllocationStrategy"]
