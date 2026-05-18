#!/usr/bin/env python3
from typing import Optional, Literal

from core.modules.market_profile.profile import MarketProfile
from core.modules.strategy.engines.simulator.capital_allocation.data_classes.account import Account
from core.modules.strategy.engines.simulator.capital_allocation.helpers.insufficient_funds import (
    resolve_shares_when_insufficient,
)
from .fees import FeeCalculator


class AllocationStrategy:
    def __init__(
        self,
        mode: Literal["equal_capital", "equal_shares", "kelly"],
        initial_capital: float,
        max_portfolio_size: int,
        market_profile: MarketProfile,
        lots_per_trade: int = 1,
        kelly_fraction: float = 0.5,
        fee_calculator: Optional[FeeCalculator] = None,
        *,
        allow_buy_at_limit_up: bool = True,
        allow_sell_at_limit_down: bool = True,
        skip_trade_when_insufficient: bool = False,
    ):
        self.mode = mode
        self.initial_capital = initial_capital
        self.max_portfolio_size = max_portfolio_size
        self.market_profile = market_profile
        self.allow_buy_at_limit_up = allow_buy_at_limit_up
        self.allow_sell_at_limit_down = allow_sell_at_limit_down
        self.skip_trade_when_insufficient = skip_trade_when_insufficient
        self.lots_per_trade = lots_per_trade
        self.kelly_fraction = kelly_fraction
        self.fee_calculator = fee_calculator
        self.per_trade_capital = initial_capital / max_portfolio_size

    def calculate_shares_to_buy(
        self,
        account: Account,
        buy_price: float,
        stock_id: str,
        win_rate: Optional[float] = None,
    ) -> int:
        if self.mode == "equal_capital":
            return self._calculate_equal_capital(account, buy_price, stock_id)
        if self.mode == "equal_shares":
            return self._calculate_equal_shares(account, buy_price, stock_id)
        if self.mode == "kelly":
            return self._calculate_kelly(account, buy_price, stock_id, win_rate)
        return 0

    def _floor_buy_shares(self, shares: int, stock_id: str) -> int:
        return self.market_profile.floor_buy_quantity(max(int(shares), 0), stock_id)

    def _min_buy_shares(self, stock_id: str) -> int:
        lot = self.market_profile.resolve_lot_rules(stock_id)
        return self._floor_buy_shares(lot.min_lot, stock_id)

    def _resolve_planned(
        self,
        *,
        planned_shares: int,
        stock_id: str,
        account: Account,
        buy_price: float,
        available_cash: Optional[float] = None,
    ) -> int:
        return resolve_shares_when_insufficient(
            planned_shares=planned_shares,
            min_lot_shares=self._min_buy_shares(stock_id),
            account=account,
            buy_price=buy_price,
            skip_trade_when_insufficient=self.skip_trade_when_insufficient,
            fee_calculator=self.fee_calculator,
            available_cash=available_cash,
            floor_shares_fn=lambda cap: self._floor_buy_shares(cap, stock_id),
        )

    def _calculate_equal_capital(self, account: Account, buy_price: float, stock_id: str) -> int:
        if account.cash < self.per_trade_capital:
            return 0
        planned = self._floor_buy_shares(int(self.per_trade_capital / buy_price), stock_id)
        return self._resolve_planned(
            planned_shares=planned,
            stock_id=stock_id,
            account=account,
            buy_price=buy_price,
            available_cash=min(account.cash, self.per_trade_capital),
        )

    def _calculate_equal_shares(self, account: Account, buy_price: float, stock_id: str) -> int:
        lot = self.market_profile.resolve_lot_rules(stock_id)
        planned = self._floor_buy_shares(lot.min_lot * self.lots_per_trade, stock_id)
        return self._resolve_planned(
            planned_shares=planned,
            stock_id=stock_id,
            account=account,
            buy_price=buy_price,
        )

    def _calculate_kelly(
        self,
        account: Account,
        buy_price: float,
        stock_id: str,
        win_rate: Optional[float] = None,
    ) -> int:
        if win_rate is None:
            return 0
        f_raw = 2 * win_rate - 1
        if f_raw <= 0:
            return 0
        kelly_divisor = 1.0 / self.kelly_fraction if self.kelly_fraction > 0 else 1.0
        target_capital = (f_raw / kelly_divisor) * account.cash
        planned = self._floor_buy_shares(int(target_capital / buy_price), stock_id)
        return self._resolve_planned(
            planned_shares=planned,
            stock_id=stock_id,
            account=account,
            buy_price=buy_price,
        )


__all__ = ["AllocationStrategy"]
