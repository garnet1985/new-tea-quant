"""资金层投资汇总（由买卖 Trade 合成）。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .trade import Trade


@dataclass
class PortfolioInvestment:
    """一笔资金层投资记录（由买入 Trade + 卖出 Trade 汇总）。"""

    investment_id: str = ""
    entity_id: str = ""
    buy_date: str = ""
    sell_date: str = ""
    buy_price: float = 0.0
    sell_price: float = 0.0
    shares: int = 0
    # 含费用后的单位成本
    average_cost: float = 0.0
    total_cost: float = 0.0
    fees: float = 0.0
    # 已实现盈亏（realized profit）：sell share value − purchase share value
    realized_profit: float = 0.0
    # roi: return on investment = realized_profit / total_cost
    roi: float = 0.0
    holding_days: int = 0
    lifecycle: str = "open"
    buy_trade: Optional[Trade] = None
    sell_trades: List[Trade] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        out = asdict(self)
        if self.buy_trade is not None:
            out["buy_trade"] = self.buy_trade.to_dict()
        out["sell_trades"] = [t.to_dict() for t in self.sell_trades]
        return out

    @classmethod
    def from_trades(
        cls,
        buy_trade: Trade,
        sell_trades: Optional[List[Trade]] = None,
    ) -> "PortfolioInvestment":
        if not buy_trade.is_buy():
            raise ValueError("buy_trade must be a buy trade")
        sells = list(sell_trades or [])
        total_cost = float(
            buy_trade.total_cost
            if buy_trade.total_cost is not None
            else (buy_trade.amount + buy_trade.fees)
        )
        shares = int(buy_trade.shares or 0)
        average_cost = (total_cost / shares) if shares > 0 else 0.0
        fees = float(buy_trade.fees or 0.0) + sum(float(t.fees or 0.0) for t in sells)
        # realized_profit：按 share value 变化汇总（不含 fees）
        buy_price = float(buy_trade.price or 0.0)
        realized_profit = 0.0
        for sell in sells:
            if sell.profit is not None:
                realized_profit += float(sell.profit)
            else:
                realized_profit += Trade.share_value_profit(
                    int(sell.shares or 0),
                    float(sell.price or 0.0),
                    buy_price,
                )
        roi = (realized_profit / total_cost) if total_cost > 0 else 0.0

        sell_date = ""
        sell_price = 0.0
        if sells:
            last_sell = max(sells, key=lambda t: str(t.date or ""))
            sell_date = str(last_sell.date or "").strip()
            sell_price = float(last_sell.price or 0.0)

        holding_days = cls._holding_days(buy_trade.date, sell_date)
        lifecycle = "complete" if sells else "open"

        return cls(
            investment_id=str(buy_trade.investment_id or "").strip(),
            entity_id=str(buy_trade.entity_id or "").strip(),
            buy_date=str(buy_trade.date or "").strip(),
            sell_date=sell_date,
            buy_price=float(buy_trade.price or 0.0),
            sell_price=sell_price,
            shares=shares,
            average_cost=average_cost,
            total_cost=total_cost,
            fees=fees,
            realized_profit=realized_profit,
            roi=roi,
            holding_days=holding_days,
            lifecycle=lifecycle,
            buy_trade=buy_trade,
            sell_trades=sells,
        )

    @staticmethod
    def _holding_days(buy_date: str, sell_date: str) -> int:
        start = str(buy_date or "").strip()
        end = str(sell_date or "").strip()
        if not start or not end:
            return 0
        try:
            start_dt = datetime.strptime(start, "%Y%m%d")
            end_dt = datetime.strptime(end, "%Y%m%d")
            return max((end_dt - start_dt).days, 0)
        except ValueError:
            return 0
