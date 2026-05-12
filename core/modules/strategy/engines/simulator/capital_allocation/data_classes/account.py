#!/usr/bin/env python3
"""账户和持仓模型。"""

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class Position:
    stock_id: str
    shares: int = 0
    avg_cost: float = 0.0
    realized_pnl: float = 0.0
    current_opportunity_id: Optional[str] = None

    def get_market_value(self, current_price: float) -> float:
        return self.shares * current_price

    def get_unrealized_pnl(self, current_price: float) -> float:
        if self.shares == 0:
            return 0.0
        return (current_price - self.avg_cost) * self.shares


@dataclass
class Account:
    initial_cash: float
    cash: float
    positions: Dict[str, Position] = field(default_factory=dict)

    def get_position(self, stock_id: str) -> Optional[Position]:
        return self.positions.get(stock_id)

    def has_position(self, stock_id: str) -> bool:
        pos = self.positions.get(stock_id)
        return pos is not None and pos.shares > 0

    def get_equity(self, stock_prices: Dict[str, float]) -> float:
        equity = self.cash
        for stock_id, position in self.positions.items():
            if position.shares > 0:
                current_price = stock_prices.get(stock_id, position.avg_cost)
                equity += position.get_market_value(current_price)
        return equity

    def get_portfolio_size(self) -> int:
        return sum(1 for pos in self.positions.values() if pos.shares > 0)
