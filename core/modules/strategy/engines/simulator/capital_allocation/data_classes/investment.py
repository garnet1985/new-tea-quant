#!/usr/bin/env python3
"""Capital allocation investment model."""

from dataclasses import dataclass, field
from typing import Any, List, Optional

from core.modules.strategy.engines.shared.data_classes import BaseInvestment
from core.modules.strategy.engines.simulator.capital_allocation.data_classes.trade import Trade
from core.modules.strategy.enums import OpportunityStatus


@dataclass
class CapitalAllocationInvestment(BaseInvestment):
    shares: int = 0
    avg_cost: float = 0.0
    commission: float = 0.0
    stamp_duty: float = 0.0
    transfer_fee: float = 0.0
    total_cost: float = 0.0
    realized_pnl: float = 0.0
    buy_trade: Optional[Trade] = None
    sell_trades: List[Trade] = field(default_factory=list)

    @classmethod
    def from_trades(
        cls,
        buy_trade: Trade,
        sell_trades: List[Trade],
        stock_name: str = "",
    ) -> "CapitalAllocationInvestment":
        if not buy_trade.is_buy():
            raise ValueError("buy_trade must be a buy trade")
        total_cost = buy_trade.total_cost or (buy_trade.amount + buy_trade.fees)
        avg_cost = total_cost / buy_trade.shares if buy_trade.shares > 0 else 0.0
        commission = buy_trade.fees
        realized_pnl = sum(t.pnl or 0.0 for t in sell_trades if t.pnl is not None)
        profit = realized_pnl
        roi = (profit / total_cost) if total_cost > 0 else 0.0

        holding_days = 0
        if buy_trade.date and sell_trades:
            last_sell = max(sell_trades, key=lambda t: t.date)
            try:
                from core.modules.strategy.engines.simulator.price_factor.helpers import parse_yyyymmdd

                start_dt = parse_yyyymmdd(buy_trade.date)
                end_dt = parse_yyyymmdd(last_sell.date)
                if start_dt and end_dt:
                    holding_days = max((end_dt - start_dt).days, 1)
            except Exception:
                pass

        if not sell_trades:
            status = OpportunityStatus.OPEN.value
        elif all(t.shares == 0 for t in sell_trades):
            status = (
                OpportunityStatus.WIN.value
                if profit > 0
                else (OpportunityStatus.LOSS.value if profit < 0 else OpportunityStatus.CLOSED.value)
            )
        else:
            status = OpportunityStatus.OPEN.value

        sell_price = None
        sell_date = None
        if sell_trades:
            last_sell = max(sell_trades, key=lambda t: t.date)
            sell_price = last_sell.price
            sell_date = last_sell.date

        return cls(
            investment_id=f"ca_{buy_trade.opportunity_id}_{buy_trade.date}",
            opportunity_id=buy_trade.opportunity_id,
            stock_id=buy_trade.stock_id,
            stock_name=stock_name,
            buy_date=buy_trade.date,
            sell_date=sell_date,
            buy_price=buy_trade.price,
            sell_price=sell_price,
            profit=profit,
            roi=roi,
            holding_days=holding_days,
            status=status,
            shares=buy_trade.shares,
            avg_cost=avg_cost,
            commission=commission,
            stamp_duty=0.0,
            transfer_fee=0.0,
            total_cost=total_cost,
            realized_pnl=realized_pnl,
            buy_trade=buy_trade,
            sell_trades=sell_trades,
        )

    @classmethod
    def from_source(cls, source: Any) -> "CapitalAllocationInvestment":
        if isinstance(source, dict):
            buy_trade_data = source.get("buy_trade")
            sell_trades_data = source.get("sell_trades", [])
            stock_name = source.get("stock_name", "")
            buy_trade = Trade.from_dict(buy_trade_data) if buy_trade_data else None
            sell_trades = [Trade.from_dict(t) for t in sell_trades_data] if sell_trades_data else []
            if buy_trade:
                return cls.from_trades(buy_trade, sell_trades, stock_name)
        raise ValueError(f"Unsupported source type: {type(source)}")
