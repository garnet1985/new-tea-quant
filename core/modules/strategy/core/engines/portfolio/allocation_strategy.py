"""仓位 sizing：equal_capital / equal_shares / kelly（类导出）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Tuple

from core.modules.market_profile.core.base.market_base_rules import MarketBaseRules
from core.modules.strategy.core.engines.portfolio.data_class.account import Account
from core.modules.strategy.core.engines.portfolio.fee_calculator import FeeCalculator
from core.modules.strategy.core.engines.shared.services.strategy_settings.portfolio_settings import (
    AllocationConfig,
    PortfolioSettings,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.simulation_settings import (
    LiquidityConfig,
)


@dataclass
class AllocationStrategy:
    """按配置计算买入股数（只算多少，不选谁）。"""

    mode: str
    initial_capital: float
    max_portfolio_size: int
    lots_per_trade: int
    kelly_fraction: float
    skip_trade_when_insufficient: bool
    market_rules: MarketBaseRules
    fee_calculator: FeeCalculator
    liquidity: LiquidityConfig = field(default_factory=LiquidityConfig)

    @classmethod
    def create(
        cls,
        *,
        portfolio: PortfolioSettings,
        market_rules: MarketBaseRules,
        fee_calculator: Optional[FeeCalculator] = None,
        liquidity: Optional[LiquidityConfig] = None,
    ) -> "AllocationStrategy":
        alloc: AllocationConfig = portfolio.allocation
        mode = str(alloc.mode or "equal_capital").strip().lower()
        if mode == "custom":
            mode = "equal_capital"
        if mode not in {"equal_capital", "equal_shares", "kelly"}:
            raise ValueError(f"unsupported allocation.mode: {alloc.mode!r}")
        return cls(
            mode=mode,
            initial_capital=float(portfolio.initial_capital),
            max_portfolio_size=int(alloc.max_portfolio_size),
            lots_per_trade=max(int(alloc.lots_per_trade or 1), 1),
            kelly_fraction=float(alloc.kelly_fraction),
            skip_trade_when_insufficient=bool(alloc.skip_trade_when_insufficient),
            market_rules=market_rules,
            fee_calculator=fee_calculator or FeeCalculator(),
            liquidity=liquidity or LiquidityConfig(),
        )

    @property
    def per_trade_capital(self) -> float:
        size = max(int(self.max_portfolio_size), 1)
        return float(self.initial_capital) / float(size)

    def calculate_shares_to_buy(
        self,
        account: Account,
        buy_price: float,
        entity_id: str,
        *,
        win_rate: Optional[float] = None,
    ) -> int:
        px = float(buy_price or 0.0)
        if px <= 0 or account.cash <= 0:
            return 0
        if self.mode == "equal_capital":
            return self._equal_capital(account, px, entity_id)
        if self.mode == "equal_shares":
            return self._equal_shares(account, px, entity_id)
        if self.mode == "kelly":
            return self._kelly(account, px, entity_id, win_rate)
        return 0

    def floor_shares(self, shares: int, entity_id: str) -> int:
        return int(
            self.market_rules.floor_quantity_for_stock(max(int(shares), 0), entity_id)
        )

    def apply_participation(
        self,
        planned_shares: int,
        *,
        bar_volume: Optional[float],
        entity_id: str,
    ) -> Tuple[int, Optional[str]]:
        """按 ``simulation.liquidity`` 约束股数；返回 ``(shares, tag)``。"""
        return self.liquidity.apply_to_shares(
            planned_shares,
            tick_volume=bar_volume,
            floor_shares_fn=self.floor_shares,
            entity_id=entity_id,
        )

    def min_buy_shares(self, entity_id: str) -> int:
        lot = self.market_rules.resolve_lot_size(entity_id)
        return self.floor_shares(int(lot.min_lot), entity_id)

    def _equal_capital(self, account: Account, buy_price: float, entity_id: str) -> int:
        if float(account.cash) < self.per_trade_capital:
            return 0
        planned = self.floor_shares(int(self.per_trade_capital / buy_price), entity_id)
        return self._resolve_planned(
            planned_shares=planned,
            entity_id=entity_id,
            cash=min(float(account.cash), self.per_trade_capital),
            buy_price=buy_price,
        )

    def _equal_shares(self, account: Account, buy_price: float, entity_id: str) -> int:
        lot = self.market_rules.resolve_lot_size(entity_id)
        planned = self.floor_shares(
            int(lot.min_lot) * int(self.lots_per_trade), entity_id
        )
        return self._resolve_planned(
            planned_shares=planned,
            entity_id=entity_id,
            cash=float(account.cash),
            buy_price=buy_price,
        )

    def _kelly(
        self,
        account: Account,
        buy_price: float,
        entity_id: str,
        win_rate: Optional[float],
    ) -> int:
        if win_rate is None:
            return 0
        f_raw = 2.0 * float(win_rate) - 1.0
        if f_raw <= 0:
            return 0
        kelly_divisor = (
            1.0 / self.kelly_fraction if self.kelly_fraction > 0 else 1.0
        )
        target_capital = (f_raw / kelly_divisor) * float(account.cash)
        planned = self.floor_shares(int(target_capital / buy_price), entity_id)
        return self._resolve_planned(
            planned_shares=planned,
            entity_id=entity_id,
            cash=float(account.cash),
            buy_price=buy_price,
        )

    def _resolve_planned(
        self,
        *,
        planned_shares: int,
        entity_id: str,
        cash: float,
        buy_price: float,
    ) -> int:
        min_lot = self.min_buy_shares(entity_id)
        if planned_shares <= 0 or buy_price <= 0 or min_lot <= 0:
            return 0
        if self.fee_calculator.buy_total_cost(min_lot * buy_price) > cash:
            return 0
        if self.fee_calculator.buy_total_cost(planned_shares * buy_price) <= cash:
            return planned_shares
        if self.skip_trade_when_insufficient:
            return 0
        affordable = self._max_affordable_shares(cash, buy_price)
        return self.floor_shares(affordable, entity_id)

    def _max_affordable_shares(self, cash: float, buy_price: float) -> int:
        if cash <= 0 or buy_price <= 0:
            return 0
        denom = buy_price * (1.0 + float(self.fee_calculator.commission_rate or 0.0))
        return int(cash / denom) if denom > 0 else 0


__all__ = ["AllocationStrategy"]
