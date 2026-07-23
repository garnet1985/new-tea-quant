#!/usr/bin/env python3
"""交易记录模型。"""

from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional


@dataclass
class Trade:
    date: str
    stock_id: str
    opportunity_id: str
    side: Literal["buy", "sell"]
    shares: int
    price: float
    amount: float
    fees: float = 0.0
    total_cost: Optional[float] = None
    net_proceeds: Optional[float] = None
    pnl: Optional[float] = None
    cash_after: Optional[float] = None
    equity_after: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "date": self.date,
            "stock_id": self.stock_id,
            "opportunity_id": self.opportunity_id,
            "side": self.side,
            "shares": self.shares,
            "price": self.price,
            "amount": self.amount,
            "fees": self.fees,
        }
        if self.total_cost is not None:
            result["total_cost"] = self.total_cost
        if self.net_proceeds is not None:
            result["net_proceeds"] = self.net_proceeds
        if self.pnl is not None:
            result["pnl"] = self.pnl
        if self.cash_after is not None:
            result["cash_after"] = self.cash_after
        if self.equity_after is not None:
            result["equity_after"] = self.equity_after
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Trade":
        return cls(
            date=data.get("date", ""),
            stock_id=data.get("stock_id", ""),
            opportunity_id=data.get("opportunity_id", ""),
            side=data.get("side", "buy"),
            shares=int(data.get("shares", 0)),
            price=float(data.get("price", 0.0)),
            amount=float(data.get("amount", 0.0)),
            fees=float(data.get("fees", 0.0)),
            total_cost=data.get("total_cost"),
            net_proceeds=data.get("net_proceeds"),
            pnl=data.get("pnl"),
            cash_after=data.get("cash_after"),
            equity_after=data.get("equity_after"),
        )

    def is_buy(self) -> bool:
        return self.side == "buy"

    def is_sell(self) -> bool:
        return self.side == "sell"
