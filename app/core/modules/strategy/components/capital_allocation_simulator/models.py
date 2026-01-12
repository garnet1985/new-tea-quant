#!/usr/bin/env python3
"""
账户和持仓模型

定义 Account 和 Position 数据结构
"""

from typing import Dict, Optional
from dataclasses import dataclass, field


@dataclass
class Position:
    """持仓信息"""
    stock_id: str
    shares: int = 0
    avg_cost: float = 0.0  # 含交易成本摊薄后的平均成本
    realized_pnl: float = 0.0  # 已实现盈亏
    current_opportunity_id: Optional[str] = None  # 当前持仓对应的机会 ID

    def get_market_value(self, current_price: float) -> float:
        """计算当前市值"""
        return self.shares * current_price

    def get_unrealized_pnl(self, current_price: float) -> float:
        """计算未实现盈亏"""
        if self.shares == 0:
            return 0.0
        return (current_price - self.avg_cost) * self.shares


@dataclass
class Account:
    """账户信息"""
    initial_cash: float
    cash: float  # 当前可用现金
    positions: Dict[str, Position] = field(default_factory=dict)  # stock_id -> Position

    def get_position(self, stock_id: str) -> Optional[Position]:
        """获取持仓"""
        return self.positions.get(stock_id)

    def has_position(self, stock_id: str) -> bool:
        """是否持有该股票"""
        pos = self.positions.get(stock_id)
        return pos is not None and pos.shares > 0

    def get_equity(self, stock_prices: Dict[str, float]) -> float:
        """
        计算总资产（现金 + 持仓市值）
        
        Args:
            stock_prices: stock_id -> current_price 的映射
        """
        equity = self.cash
        for stock_id, position in self.positions.items():
            if position.shares > 0:
                current_price = stock_prices.get(stock_id, position.avg_cost)
                equity += position.get_market_value(current_price)
        return equity

    def get_portfolio_size(self) -> int:
        """获取当前持仓股票数量"""
        return sum(1 for pos in self.positions.values() if pos.shares > 0)
