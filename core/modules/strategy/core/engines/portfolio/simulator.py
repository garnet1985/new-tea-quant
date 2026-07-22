"""Portfolio 账户事件回放（类导出）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from core.modules.strategy.core.engines.portfolio.allocation_strategy import (
    AllocationStrategy,
)
from core.modules.strategy.core.engines.portfolio.data_class import (
    Account,
    PortfolioEvent,
    Position,
    Trade,
)
from core.modules.strategy.core.engines.portfolio.fee_calculator import FeeCalculator


@dataclass
class OpenLot:
    """已买入、待卖出的一笔投资。"""

    investment_id: str
    entity_id: str
    shares: int
    buy_price: float
    buy_date: str


@dataclass
class PortfolioSimResult:
    """回放结果。"""

    account: Account
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[Dict[str, float | int | str]] = field(default_factory=list)
    skipped_buys: int = 0
    skipped_sells: int = 0
    completed_count: int = 0
    win_count: int = 0

    @property
    def success(self) -> bool:
        return True


@dataclass
class PortfolioSimulator:
    """按事件序回放买卖，更新账户。"""

    allocation: AllocationStrategy
    fee_calculator: FeeCalculator
    save_equity_curve: bool = True

    @classmethod
    def create(
        cls,
        *,
        allocation: AllocationStrategy,
        fee_calculator: FeeCalculator,
        save_equity_curve: bool = True,
    ) -> "PortfolioSimulator":
        return cls(
            allocation=allocation,
            fee_calculator=fee_calculator,
            save_equity_curve=save_equity_curve,
        )

    def run(
        self,
        events: Sequence[PortfolioEvent],
        *,
        initial_capital: float,
    ) -> PortfolioSimResult:
        account = Account(
            initial_cash=float(initial_capital),
            cash=float(initial_capital),
        )
        result = PortfolioSimResult(account=account)
        open_lots: Dict[str, OpenLot] = {}
        current_date = ""

        for event in events:
            date = str(event.date or "").strip()
            if self.save_equity_curve and current_date and date != current_date:
                self._append_equity(result, current_date)
            if date:
                current_date = date

            if event.is_buy():
                self._handle_buy(event, account, open_lots, result)
            elif event.is_sell():
                self._handle_sell(event, account, open_lots, result)

        if self.save_equity_curve and current_date:
            self._append_equity(result, current_date)
        return result

    def _handle_buy(
        self,
        event: PortfolioEvent,
        account: Account,
        open_lots: Dict[str, OpenLot],
        result: PortfolioSimResult,
    ) -> None:
        entity_id = str(event.entity_id or "").strip()
        inv_id = str(event.investment_id or "").strip()
        price = float(event.price or 0.0)
        if not entity_id or not inv_id or price <= 0:
            result.skipped_buys += 1
            return
        if account.has_position(entity_id):
            result.skipped_buys += 1
            return
        if account.open_position_count() >= self.allocation.max_portfolio_size:
            result.skipped_buys += 1
            return
        if inv_id in open_lots:
            result.skipped_buys += 1
            return

        win_rate = self._win_rate(result)
        shares = self.allocation.calculate_shares_to_buy(
            account,
            price,
            entity_id,
            win_rate=win_rate if self.allocation.mode == "kelly" else None,
        )
        if shares <= 0:
            result.skipped_buys += 1
            return

        fees = self.fee_calculator.calculate_fees(shares * price, "buy")
        trade = Trade.make_buy(
            date=event.date,
            entity_id=entity_id,
            investment_id=inv_id,
            shares=shares,
            price=price,
            fees=fees,
        )
        total_cost = float(trade.total_cost or (trade.amount + trade.fees))
        if total_cost > account.cash:
            result.skipped_buys += 1
            return

        account.cash -= total_cost
        account.positions[entity_id] = Position(
            entity_id=entity_id,
            shares=shares,
            average_cost=total_cost / shares if shares > 0 else price,
            current_investment_id=inv_id,
        )
        open_lots[inv_id] = OpenLot(
            investment_id=inv_id,
            entity_id=entity_id,
            shares=shares,
            buy_price=price,
            buy_date=str(event.date or ""),
        )
        trade.cash_after = account.cash
        trade.equity_after = account.equity({entity_id: price})
        result.trades.append(trade)

    def _handle_sell(
        self,
        event: PortfolioEvent,
        account: Account,
        open_lots: Dict[str, OpenLot],
        result: PortfolioSimResult,
    ) -> None:
        inv_id = str(event.investment_id or "").strip()
        lot = open_lots.get(inv_id)
        if lot is None:
            result.skipped_sells += 1
            return
        entity_id = lot.entity_id
        position = account.get_position(entity_id)
        if position is None or position.shares <= 0:
            result.skipped_sells += 1
            open_lots.pop(inv_id, None)
            return

        sell_price = float(event.price or 0.0)
        shares = int(position.shares)
        fees = self.fee_calculator.calculate_fees(shares * sell_price, "sell")
        trade = Trade.make_sell(
            date=event.date,
            entity_id=entity_id,
            investment_id=inv_id,
            shares=shares,
            sell_price=sell_price,
            buy_price=lot.buy_price,
            fees=fees,
        )
        net = float(trade.net_proceeds if trade.net_proceeds is not None else trade.amount - fees)
        account.cash += net
        position.realized_profit += float(trade.profit or 0.0)
        position.shares = 0
        position.current_investment_id = None
        open_lots.pop(inv_id, None)

        trade.cash_after = account.cash
        trade.equity_after = account.equity({entity_id: sell_price})
        result.trades.append(trade)
        result.completed_count += 1
        if float(trade.profit or 0.0) > 0:
            result.win_count += 1

    def _win_rate(self, result: PortfolioSimResult) -> float:
        if result.completed_count <= 0:
            return 0.5
        return float(result.win_count) / float(result.completed_count)

    def _append_equity(self, result: PortfolioSimResult, date: str) -> None:
        account = result.account
        result.equity_curve.append(
            {
                "date": date,
                "cash": float(account.cash),
                "equity": float(account.equity({})),
                "open_positions": int(account.open_position_count()),
            }
        )


__all__ = ["OpenLot", "PortfolioSimResult", "PortfolioSimulator"]
