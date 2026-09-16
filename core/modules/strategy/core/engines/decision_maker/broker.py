"""决策者成交：用户股数过资金层同一把硬尺。

本文件:
- DecisionBroker: 预览 / 买入（用户股数）/ 纪律卖出
  边界: 不调用 AllocationStrategy.calculate_shares_to_buy；手数 / 流动性 / 现金 / 组合上限同模拟器
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Set, Tuple

from core.modules.strategy.core.engines.decision_maker.timeline import lot_key
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
from core.modules.strategy.core.engines.portfolio.simulator import OpenLot


@dataclass(frozen=True)
class BrokerError:
    message: str


@dataclass(frozen=True)
class BuyPreview:
    shares: int
    price: float
    notional: float
    total_cost: float
    fees: float


class DecisionBroker:
    """对 Account / open_lots 应用一笔用户买单或纪律卖单。"""

    def __init__(
        self,
        *,
        allocation: AllocationStrategy,
        fee_calculator: FeeCalculator,
    ) -> None:
        self.allocation = allocation
        self.fee_calculator = fee_calculator

    def preview_buy(
        self,
        event: PortfolioEvent,
        shares: int,
        account: Account,
        open_lots: Dict[str, OpenLot],
        *,
        extra_slots: int = 1,
        draft_entities: Optional[Set[str]] = None,
    ) -> Tuple[Optional[BuyPreview], Optional[BrokerError]]:
        err = self._reject_buy(
            event,
            shares,
            account,
            open_lots,
            extra_slots=extra_slots,
            draft_entities=draft_entities,
        )
        if err is not None:
            return None, err
        n, part_err = self._sized_shares(event, shares)
        if part_err is not None:
            return None, part_err
        price = float(event.price or 0.0)
        notional = float(n) * price
        fees = self.fee_calculator.calculate_fees(notional, "buy")
        total = notional + fees
        if total > float(account.cash):
            return None, BrokerError("现金不足（含费用）")
        return (
            BuyPreview(
                shares=n,
                price=price,
                notional=notional,
                total_cost=total,
                fees=fees,
            ),
            None,
        )

    def apply_buy(
        self,
        event: PortfolioEvent,
        shares: int,
        account: Account,
        open_lots: Dict[str, OpenLot],
    ) -> Tuple[Optional[Trade], Optional[BrokerError]]:
        preview, err = self.preview_buy(event, shares, account, open_lots)
        if err is not None or preview is None:
            return None, err or BrokerError("无法买入")
        entity_id = str(event.entity_id or "").strip()
        inv_id = str(event.investment_id or "").strip()
        trade = Trade.make_buy(
            date=event.date,
            entity_id=entity_id,
            investment_id=inv_id,
            shares=preview.shares,
            price=preview.price,
            fees=preview.fees,
            entry_price_hfq=float(getattr(event, "entry_price_hfq", 0.0) or 0.0),
        )
        total_cost = float(trade.total_cost or (trade.amount + trade.fees))
        account.cash -= total_cost
        account.positions[entity_id] = Position(
            entity_id=entity_id,
            shares=preview.shares,
            average_cost=total_cost / preview.shares if preview.shares > 0 else preview.price,
            current_investment_id=inv_id,
        )
        open_lots[lot_key(entity_id, inv_id)] = OpenLot(
            investment_id=inv_id,
            entity_id=entity_id,
            shares=preview.shares,
            buy_price=preview.price,
            buy_date=str(event.date or ""),
            entry_price_hfq=float(getattr(event, "entry_price_hfq", 0.0) or 0.0),
            initial_shares=preview.shares,
        )
        trade.cash_after = account.cash
        trade.equity_after = account.equity({entity_id: preview.price})
        return trade, None

    def apply_sell(
        self,
        event: PortfolioEvent,
        account: Account,
        open_lots: Dict[str, OpenLot],
        *,
        is_last: bool = True,
    ) -> Tuple[Optional[Trade], Optional[str]]:
        """纪律卖出。未持有该 lot 则跳过（用户没买）。返回 (trade, skip_reason)。

        卖出数量跟枚举切片 ``exit_ratio``，中间笔向下取整到手；最后一笔清空（含零股）。
        不再按当日量二次 clip。
        """
        inv_id = str(event.investment_id or "").strip()
        entity_id = str(event.entity_id or "").strip()
        key = lot_key(entity_id, inv_id)
        lot = open_lots.get(key)
        if lot is None:
            return None, "not_held"
        entity_id = lot.entity_id
        position = account.get_position(entity_id)
        if position is None or position.shares <= 0:
            open_lots.pop(key, None)
            return None, "empty"
        buy_price = float(lot.buy_price or 0.0)
        if buy_price <= 0:
            return None, "bad_price"
        remaining = int(position.shares)
        shares = self.allocation.size_sell_shares(
            remaining=remaining,
            initial_shares=int(lot.initial_shares or remaining),
            exit_ratio=getattr(event, "exit_ratio", 1.0),
            entity_id=entity_id,
            is_last=is_last,
        )
        if shares <= 0:
            return None, "empty"
        roi = Trade.finite_roi(event.roi)
        proceeds = Trade.equivalent_exit_value(shares, buy_price, roi)
        fees = self.fee_calculator.calculate_fees(proceeds, "sell")
        trade = Trade.make_sell(
            date=event.date,
            entity_id=entity_id,
            investment_id=inv_id,
            shares=shares,
            buy_price=buy_price,
            roi=roi,
            fees=fees,
        )
        net = float(
            trade.net_proceeds if trade.net_proceeds is not None else trade.amount - fees
        )
        account.cash += net
        position.realized_profit += float(trade.profit or 0.0)
        position.shares = max(0, remaining - shares)
        if position.shares <= 0:
            position.current_investment_id = None
            open_lots.pop(key, None)
            if entity_id in account.positions and account.positions[entity_id].shares <= 0:
                account.positions.pop(entity_id, None)
        else:
            lot.shares = int(position.shares)
        trade.cash_after = account.cash
        trade.equity_after = account.equity({entity_id: float(trade.price or 0.0)})
        return trade, None

    def _reject_buy(
        self,
        event: PortfolioEvent,
        shares: int,
        account: Account,
        open_lots: Dict[str, OpenLot],
        *,
        extra_slots: int = 1,
        draft_entities: Optional[Set[str]] = None,
    ) -> Optional[BrokerError]:
        entity_id = str(event.entity_id or "").strip()
        inv_id = str(event.investment_id or "").strip()
        price = float(event.price or 0.0)
        if not entity_id or not inv_id or price <= 0:
            return BrokerError("机会无效")
        try:
            n = int(shares)
        except (TypeError, ValueError):
            return BrokerError("股数须为正整数")
        if n <= 0:
            return BrokerError("股数须为正整数")
        floored = self.allocation.floor_shares(n, entity_id)
        if floored != n:
            min_lot = self.allocation.min_buy_shares(entity_id)
            return BrokerError(f"股数须符合手数（最小 {min_lot} 股）")
        if n < self.allocation.min_buy_shares(entity_id):
            return BrokerError(
                f"低于最小手数（{self.allocation.min_buy_shares(entity_id)} 股）"
            )
        if account.has_position(entity_id):
            return BrokerError("已持有该标的，不能再开仓")
        reserved = set(draft_entities or ())
        reserved.discard(entity_id)
        if entity_id in reserved:
            return BrokerError("当日草稿已选同一标的")
        if lot_key(entity_id, inv_id) in open_lots:
            return BrokerError("该笔机会已在持仓")
        projected = account.open_position_count() + max(int(extra_slots), 0)
        if projected > int(self.allocation.max_portfolio_size):
            return BrokerError(
                f"超过组合上限（max_portfolio_size={self.allocation.max_portfolio_size}）"
            )
        return None

    def _sized_shares(
        self,
        event: PortfolioEvent,
        shares: int,
    ) -> Tuple[int, Optional[BrokerError]]:
        entity_id = str(event.entity_id or "").strip()
        n = int(shares)
        sized, tag = self.allocation.apply_participation(
            n,
            bar_volume=event.bar_volume,
            entity_id=entity_id,
        )
        if tag in (
            self.allocation.liquidity.TAG_SKIP,
            self.allocation.liquidity.TAG_CLIP_ZERO,
        ) or sized <= 0:
            return 0, BrokerError("超过当日流动性，下不成")
        if tag == self.allocation.liquidity.TAG_CLIPPED and sized < n:
            return 0, BrokerError(f"超过当日流动性，最多 {sized} 股")
        return sized, None


__all__ = ["BrokerError", "BuyPreview", "DecisionBroker"]
