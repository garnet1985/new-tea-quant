"""Portfolio 账户事件回放。

本文件:
- PortfolioSimulator: 按 PortfolioEvent 序更新 Account、生成 Trade / equity_curve
- PortfolioSimResult / OpenLot: 回放结果与在途 lot
  边界: 负责资金层事件回放；不负责选仓（EnterSelection）或 enum 读盘
"""

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


def _lot_key(entity_id: str, investment_id: str) -> str:
    """开仓索引键：必须带 entity，否则跨股 investment_id 会串单。"""
    return f"{str(entity_id or '').strip()}\t{str(investment_id or '').strip()}"


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
    buy_participation_skip: int = 0
    buy_participation_clipped: int = 0
    sell_participation_skip: int = 0
    sell_participation_clipped: int = 0

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
        lot_key = _lot_key(entity_id, inv_id)
        if lot_key in open_lots:
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

        shares, part_tag = self.allocation.apply_participation(
            shares,
            bar_volume=event.bar_volume,
            entity_id=entity_id,
        )
        if part_tag in (
            self.allocation.liquidity.TAG_SKIP,
            self.allocation.liquidity.TAG_CLIP_ZERO,
        ):
            result.buy_participation_skip += 1
            result.skipped_buys += 1
            return
        if part_tag == self.allocation.liquidity.TAG_CLIPPED:
            result.buy_participation_clipped += 1
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
        open_lots[lot_key] = OpenLot(
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
        entity_id = str(event.entity_id or "").strip()
        lot_key = _lot_key(entity_id, inv_id)
        lot = open_lots.get(lot_key)
        if lot is None:
            result.skipped_sells += 1
            return
        entity_id = lot.entity_id
        position = account.get_position(entity_id)
        if position is None or position.shares <= 0:
            result.skipped_sells += 1
            open_lots.pop(lot_key, None)
            return

        sell_price = float(event.price or 0.0)
        shares = int(position.shares)
        shares, part_tag = self.allocation.apply_participation(
            shares,
            bar_volume=event.bar_volume,
            entity_id=entity_id,
        )
        if part_tag in (
            self.allocation.liquidity.TAG_SKIP,
            self.allocation.liquidity.TAG_CLIP_ZERO,
        ):
            result.sell_participation_skip += 1
            result.skipped_sells += 1
            return
        if part_tag == self.allocation.liquidity.TAG_CLIPPED:
            result.sell_participation_clipped += 1
        if shares <= 0:
            result.skipped_sells += 1
            return

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
        position.shares = max(0, int(position.shares) - shares)
        if position.shares <= 0:
            position.current_investment_id = None
            open_lots.pop(lot_key, None)
            result.completed_count += 1
            if float(trade.profit or 0.0) > 0:
                result.win_count += 1
        else:
            # 参与率砍量后仍有剩余仓位：更新 open lot，等后续卖出事件（若有）
            lot.shares = int(position.shares)

        trade.cash_after = account.cash
        trade.equity_after = account.equity({entity_id: sell_price})
        result.trades.append(trade)

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
