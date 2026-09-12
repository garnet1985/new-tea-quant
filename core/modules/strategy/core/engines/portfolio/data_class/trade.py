"""Portfolio 成交记录 data class。

本文件:
- Trade: 单笔 buy/sell 成交；卖出盈利 = 股数 × 买入 raw × hfq ROI
  边界: 负责成交记录结构；不负责 FeeCalculator 或 Account 更新
"""

from __future__ import annotations

import math
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
    # 本笔实现的盈亏：股数 × 买入 raw × hfq ROI（不含 fees）；通常卖出腿填写
    profit: Optional[float] = None
    cash_after: Optional[float] = None
    equity_after: Optional[float] = None
    # 买入成交后复权价；日频盯市 ROI 分母。卖出腿可空。
    entry_price_hfq: float = 0.0

    def is_buy(self) -> bool:
        return str(self.side or "").strip().lower() == "buy"

    def is_sell(self) -> bool:
        return str(self.side or "").strip().lower() == "sell"

    @staticmethod
    def purchase_share_value(shares: int, buy_price: float) -> float:
        """买入时股份市值（shares × buy_price，不含 fees）。"""
        return float(shares) * float(buy_price)

    @staticmethod
    def hfq_cash_profit(shares: int, buy_price: float, roi: float) -> float:
        """平仓盈利 = 买入股数 × 买入 raw × hfq ROI（不含 fees）。"""
        return float(shares) * float(buy_price) * float(roi)

    @staticmethod
    def equivalent_exit_value(shares: int, buy_price: float, roi: float) -> float:
        """同股等价卖出额 = 本金 + 盈利；不是交易所 raw 打印价 × 股数。"""
        return Trade.purchase_share_value(shares, buy_price) + Trade.hfq_cash_profit(
            shares, buy_price, roi
        )

    @staticmethod
    def finite_roi(roi: Any) -> float:
        try:
            value = float(roi or 0.0)
        except (TypeError, ValueError):
            return 0.0
        if not math.isfinite(value):
            return 0.0
        return value

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
        entry_price_hfq: float = 0.0,
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
            entry_price_hfq=float(entry_price_hfq or 0.0),
        )

    @classmethod
    def make_sell(
        cls,
        *,
        date: str,
        entity_id: str,
        investment_id: str,
        shares: int,
        buy_price: float,
        roi: float,
        fees: float = 0.0,
    ) -> "Trade":
        """卖出：现金与盈利按 hfq ROI，不用 exit_raw 当成交额。

        ``price`` / ``amount`` 为同股等价价与卖出额（``买入 raw × (1 + ROI)``），
        不是交易所 raw 打印价。
        """
        n = int(shares)
        buy_px = float(buy_price)
        if n <= 0:
            raise ValueError("sell shares 必须 > 0")
        if buy_px <= 0:
            raise ValueError("buy_price (raw) 必须 > 0")
        roi_value = cls.finite_roi(roi)
        profit = cls.hfq_cash_profit(n, buy_px, roi_value)
        amount = cls.equivalent_exit_value(n, buy_px, roi_value)
        px = amount / float(n)
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
            profit=profit,
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
        if self.is_buy() or float(self.entry_price_hfq or 0.0) > 0:
            out["entry_price_hfq"] = float(self.entry_price_hfq or 0.0)
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
            entry_price_hfq=float(raw.get("entry_price_hfq") or 0.0),
        )

    @staticmethod
    def _optional_float(value: Any) -> Optional[float]:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
