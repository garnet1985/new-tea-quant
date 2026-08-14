"""Portfolio 成交记录 data class。

本文件:
- Trade: 单笔 buy/sell 成交；profit = sell share value − purchase share value
  边界: 负责成交记录结构；不负责 FeeCalculator 或 Account 更新
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class Trade:
    """一笔资金层成交。"""

    date: str
    entity_id: str
    investment_id: str
    side: str
    shares: int
    price: float
    amount: float
    fees: float = 0.0
    total_cost: Optional[float] = None
    net_proceeds: Optional[float] = None
    # 本笔实现的盈亏：share value 变化（不含 fees）；通常卖出腿填写
    profit: Optional[float] = None
    cash_after: Optional[float] = None
    equity_after: Optional[float] = None

    def is_buy(self) -> bool:
        return str(self.side or "").strip().lower() == "buy"

    def is_sell(self) -> bool:
        return str(self.side or "").strip().lower() == "sell"

    @staticmethod
    def purchase_share_value(shares: int, buy_price: float) -> float:
        """买入时股份市值（shares × buy_price，不含 fees）。"""
        return float(shares) * float(buy_price)

    @staticmethod
    def sell_share_value(shares: int, sell_price: float) -> float:
        """卖出时股份市值（shares × sell_price，不含 fees）。"""
        return float(shares) * float(sell_price)

    @staticmethod
    def share_value_profit(
        shares: int,
        sell_price: float,
        buy_price: float,
    ) -> float:
        """profit = sell share value − purchase share value。"""
        return Trade.sell_share_value(shares, sell_price) - Trade.purchase_share_value(
            shares, buy_price
        )

    @classmethod
    def make_buy(
        cls,
        *,
        date: str,
        entity_id: str,
        investment_id: str,
        shares: int,
        price: float,
        fees: float = 0.0,
    ) -> "Trade":
        """买入：``price`` 必须为 raw（不复权）。"""
        n = int(shares)
        px = float(price)
        if px <= 0:
            raise ValueError("buy price (raw) 必须 > 0")
        if n <= 0:
            raise ValueError("buy shares 必须 > 0")
        amount = cls.purchase_share_value(n, px)
        fee = float(fees or 0.0)
        return cls(
            date=str(date or "").strip(),
            entity_id=str(entity_id or "").strip(),
            investment_id=str(investment_id or "").strip(),
            side="buy",
            shares=n,
            price=px,
            amount=amount,
            fees=fee,
            total_cost=amount + fee,
            profit=None,
        )

    @classmethod
    def make_sell(
        cls,
        *,
        date: str,
        entity_id: str,
        investment_id: str,
        shares: int,
        sell_price: float,
        buy_price: float,
        fees: float = 0.0,
    ) -> "Trade":
        """卖出：profit 按 share value 变化计算（不含 fees）。"""
        n = int(shares)
        px = float(sell_price)
        buy_px = float(buy_price)
        if n <= 0:
            raise ValueError("sell shares 必须 > 0")
        if buy_px <= 0:
            raise ValueError("buy_price (raw) 必须 > 0")
        amount = cls.sell_share_value(n, px)
        fee = float(fees or 0.0)
        return cls(
            date=str(date or "").strip(),
            entity_id=str(entity_id or "").strip(),
            investment_id=str(investment_id or "").strip(),
            side="sell",
            shares=n,
            price=px,
            amount=amount,
            fees=fee,
            net_proceeds=amount - fee,
            profit=cls.share_value_profit(n, px, buy_px),
        )

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "date": self.date,
            "entity_id": self.entity_id,
            "investment_id": self.investment_id,
            "side": self.side,
            "shares": int(self.shares),
            "price": float(self.price),
            "amount": float(self.amount),
            "fees": float(self.fees),
        }
        if self.total_cost is not None:
            out["total_cost"] = float(self.total_cost)
        if self.net_proceeds is not None:
            out["net_proceeds"] = float(self.net_proceeds)
        if self.profit is not None:
            out["profit"] = float(self.profit)
        if self.cash_after is not None:
            out["cash_after"] = float(self.cash_after)
        if self.equity_after is not None:
            out["equity_after"] = float(self.equity_after)
        return out

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Trade":
        raw = data or {}
        return cls(
            date=str(raw.get("date") or "").strip(),
            entity_id=str(raw.get("entity_id") or "").strip(),
            investment_id=str(raw.get("investment_id") or "").strip(),
            side=str(raw.get("side") or "buy").strip().lower(),
            shares=int(raw.get("shares") or 0),
            price=float(raw.get("price") or 0.0),
            amount=float(raw.get("amount") or 0.0),
            fees=float(raw.get("fees") or 0.0),
            total_cost=cls._optional_float(raw.get("total_cost")),
            net_proceeds=cls._optional_float(raw.get("net_proceeds")),
            profit=cls._optional_float(raw.get("profit")),
            cash_after=cls._optional_float(raw.get("cash_after")),
            equity_after=cls._optional_float(raw.get("equity_after")),
        )

    @staticmethod
    def _optional_float(value: Any) -> Optional[float]:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
