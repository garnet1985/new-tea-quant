#!/usr/bin/env python3
"""
交易记录模型

定义 Trade 数据结构，用于资金分配模拟器
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Literal, Optional
from datetime import datetime


@dataclass
class Trade:
    """交易记录"""
    # 基础信息
    date: str  # YYYYMMDD
    stock_id: str
    opportunity_id: str
    side: Literal["buy", "sell"]  # 交易方向
    
    # 交易信息
    shares: int  # 交易股数
    price: float  # 交易价格
    amount: float  # 交易金额（不含费用）
    
    # 费用信息
    fees: float = 0.0  # 总费用
    
    # 买入特有字段
    total_cost: Optional[float] = None  # 买入总成本（含费用）
    
    # 卖出特有字段
    net_proceeds: Optional[float] = None  # 卖出净收入（扣除费用）
    pnl: Optional[float] = None  # 盈亏（卖出时计算）
    
    # 账户状态（交易后）
    cash_after: Optional[float] = None  # 交易后现金
    equity_after: Optional[float] = None  # 交易后总资产
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
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
        
        # 买入特有字段
        if self.total_cost is not None:
            result["total_cost"] = self.total_cost
        
        # 卖出特有字段
        if self.net_proceeds is not None:
            result["net_proceeds"] = self.net_proceeds
        if self.pnl is not None:
            result["pnl"] = self.pnl
        
        # 账户状态
        if self.cash_after is not None:
            result["cash_after"] = self.cash_after
        if self.equity_after is not None:
            result["equity_after"] = self.equity_after
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Trade":
        """从字典创建 Trade"""
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
        """是否为买入交易"""
        return self.side == "buy"
    
    def is_sell(self) -> bool:
        """是否为卖出交易"""
        return self.side == "sell"
