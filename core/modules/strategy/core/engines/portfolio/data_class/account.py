"""Portfolio 账户与持仓 data class。

本文件:
- Position / Account: 资金层账户快照
  边界: 负责数据结构；不负责事件回放或 sizing
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class Position:
    """单标的持仓。"""

    entity_id: str
    shares: int = 0
    # 持仓成本均价（不复权口径）
    average_cost: float = 0.0
    # 已实现盈亏（realized profit and loss）：平仓后计入账户的损益
    realized_profit: float = 0.0
    current_investment_id: Optional[str] = None

    def market_value(self, current_price: float) -> float:
        return float(self.shares) * float(current_price)

    def unrealized_profit(self, current_price: float) -> float:
        """未实现盈亏：按现价相对 average_cost 的浮动盈亏。"""
        if self.shares <= 0:
            return 0.0
        return (float(current_price) - float(self.average_cost)) * float(self.shares)


@dataclass
class Account:
    """资金账户：现金 + 持仓。"""

    initial_cash: float
    cash: float
    positions: Dict[str, Position] = field(default_factory=dict)

    def get_position(self, entity_id: str) -> Optional[Position]:
        return self.positions.get(str(entity_id or "").strip())

    def has_position(self, entity_id: str) -> bool:
        pos = self.get_position(entity_id)
        return pos is not None and pos.shares > 0

    def open_position_count(self) -> int:
        """当前有持仓（shares > 0）的标的数量。"""
        return sum(1 for pos in self.positions.values() if pos.shares > 0)

    def equity(self, prices: Dict[str, float]) -> float:
        """总权益 = 现金 + 持仓市值；缺行情价时用 average_cost。"""
        total = float(self.cash)
        for entity_id, position in self.positions.items():
            if position.shares <= 0:
                continue
            px = float(prices.get(entity_id, position.average_cost) or position.average_cost)
            total += position.market_value(px)
        return total
