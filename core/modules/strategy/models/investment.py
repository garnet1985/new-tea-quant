#!/usr/bin/env python3
"""
投资记录模型

定义 Investment 数据结构，用于价格因子模拟器和资金分配模拟器
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime

from core.modules.strategy.models.trade import Trade


@dataclass
class BaseInvestment(ABC):
    """投资基类（统一接口）"""
    # 核心标识（无默认值的字段必须在前面）
    investment_id: str
    opportunity_id: str
    stock_id: str
    buy_date: str  # YYYYMMDD
    buy_price: float
    
    # 有默认值的字段在后面
    stock_name: str = ""
    sell_date: Optional[str] = None  # YYYYMMDD
    sell_price: Optional[float] = None
    
    # 收益信息（统一命名）
    profit: float = 0.0  # 总盈亏
    roi: float = 0.0     # 收益率
    holding_days: int = 0
    
    # 状态
    status: Literal["open", "closed", "win", "loss"] = "open"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（统一接口）"""
        return asdict(self)
    
    @classmethod
    @abstractmethod
    def from_source(cls, source: Any) -> "BaseInvestment":
        """从源数据创建 Investment（子类实现）"""
        raise NotImplementedError


@dataclass
class PriceFactorInvestment(BaseInvestment):
    """价格因子投资记录（1股，无资金约束）"""
    # PF 特有字段
    tracking: Optional[Dict[str, Any]] = None
    completed_targets: List[Dict[str, Any]] = field(default_factory=list)
    overall_annual_return: float = 0.0
    
    # 固定值
    shares: int = 1  # 固定 1 股
    
    @classmethod
    def from_opportunity(
        cls,
        opportunity: Dict[str, Any],
        targets: List[Dict[str, Any]],
        stock_name: str = ""
    ) -> "PriceFactorInvestment":
        """
        从 Opportunity 和 Targets 创建 PriceFactorInvestment
        
        Args:
            opportunity: opportunity 字典
            targets: targets 列表
            stock_name: 股票名称（可选）
        """
        opp_id = str(opportunity.get("opportunity_id", "")).strip()
        stock_id = opportunity.get("stock_id", "")
        trigger_date = opportunity.get("trigger_date", "")
        exit_date = opportunity.get("exit_date", "")
        
        try:
            trigger_price = float(opportunity.get("trigger_price", 0.0) or 0.0)
        except (ValueError, TypeError):
            trigger_price = 0.0
        
        try:
            roi = float(opportunity.get("roi", 0.0) or 0.0)
        except (ValueError, TypeError):
            roi = 0.0
        
        # 计算整体 PnL（1 股）
        if targets:
            profit = sum(float(t.get("weighted_profit", 0.0) or 0.0) for t in targets)
        else:
            # 回退：使用整体 ROI 估算
            profit = trigger_price * roi
        
        # 计算持续天数
        holding_days = 1
        if trigger_date and exit_date:
            try:
                from core.modules.strategy.components.price_factor_simulator.helpers import parse_yyyymmdd
                start_dt = parse_yyyymmdd(trigger_date)
                end_dt = parse_yyyymmdd(exit_date)
                if start_dt and end_dt:
                    holding_days = max((end_dt - start_dt).days, 1)
            except Exception:
                pass
        
        # 计算年化收益率
        overall_annual_return = 0.0
        if holding_days > 0:
            try:
                from core.modules.strategy.components.price_factor_simulator.helpers import get_annual_return
                overall_annual_return = get_annual_return(roi, holding_days)
            except Exception:
                pass
        
        # 构造 tracking
        tracking = cls._build_tracking(opportunity, trigger_price, trigger_date, exit_date)
        
        # 构造 completed_targets
        completed_targets = cls._build_completed_targets(targets, trigger_price)
        
        # 确定状态
        status_str = (opportunity.get("status") or "").lower()
        if status_str in ("win", "loss", "open"):
            status = status_str
        else:
            status = "win" if profit > 0 else ("loss" if profit < 0 else "open")
        
        # 生成 investment_id
        investment_id = f"pf_{opp_id}"
        
        return cls(
            investment_id=investment_id,
            opportunity_id=opp_id,
            stock_id=stock_id,
            stock_name=stock_name,
            buy_date=trigger_date,
            sell_date=exit_date if exit_date else None,
            buy_price=trigger_price,
            sell_price=None,  # PF 投资可能没有单一卖出价格
            profit=profit,
            roi=roi,
            holding_days=holding_days,
            status=status,
            tracking=tracking,
            completed_targets=completed_targets,
            overall_annual_return=overall_annual_return,
            shares=1,
        )
    
    @classmethod
    def from_source(cls, source: Any) -> "PriceFactorInvestment":
        """从源数据创建（兼容接口）"""
        if isinstance(source, dict):
            opportunity = source.get("opportunity", source)
            targets = source.get("targets", [])
            stock_name = source.get("stock_name", "")
            return cls.from_opportunity(opportunity, targets, stock_name)
        raise ValueError(f"Unsupported source type: {type(source)}")
    
    @staticmethod
    def _build_tracking(
        opportunity: Dict[str, Any],
        trigger_price: float,
        trigger_date: str,
        exit_date: str,
    ) -> Dict[str, Any]:
        """构造 tracking 信息"""
        try:
            max_price = float(opportunity.get("max_price", 0.0) or 0.0)
        except (ValueError, TypeError):
            max_price = 0.0
        try:
            min_price = float(opportunity.get("min_price", 0.0) or 0.0)
        except (ValueError, TypeError):
            min_price = 0.0
        
        if trigger_price > 0:
            max_ratio = (max_price - trigger_price) / trigger_price if max_price > 0 else 0.0
            min_ratio = (min_price - trigger_price) / trigger_price if min_price > 0 else 0.0
        else:
            max_ratio = 0.0
            min_ratio = 0.0
        
        return {
            "max_close_reached": {
                "price": max_price if max_price > 0 else trigger_price,
                "date": exit_date,
                "ratio": max_ratio,
            },
            "min_close_reached": {
                "price": min_price if min_price > 0 else trigger_price,
                "date": trigger_date,
                "ratio": min_ratio,
            },
        }
    
    @staticmethod
    def _build_completed_targets(
        targets: List[Dict[str, Any]],
        trigger_price: float,
    ) -> List[Dict[str, Any]]:
        """构造 completed_targets 列表"""
        completed_targets: List[Dict[str, Any]] = []
        for t in targets:
            sell_price = float(t.get("price", 0.0) or 0.0)
            profit = float(t.get("profit", 0.0) or 0.0)
            weighted_profit = float(t.get("weighted_profit", 0.0) or 0.0)
            t_roi = float(t.get("roi", 0.0) or 0.0)
            sell_ratio = float(t.get("sell_ratio", 0.0) or 0.0)
            sell_date = t.get("date", "") or ""
            reason = (t.get("reason", "") or "").lower()
            
            if "win" in reason:
                target_type = "take_profit"
                name = reason
            elif "loss" in reason:
                target_type = "stop_loss"
                name = reason
            elif "expiration" in reason:
                target_type = "expired"
                name = "expiration"
            else:
                target_type = "unknown"
                name = reason or "unknown"
            
            completed_targets.append({
                "name": name,
                "target_type": target_type,
                "sell_price": sell_price,
                "sell_date": sell_date,
                "sell_ratio": sell_ratio,
                "profit": profit,
                "weighted_profit": weighted_profit,
                "profit_ratio": t_roi,
                "target_price": trigger_price,
                "extra_fields": {},
            })
        
        return completed_targets


@dataclass
class CapitalAllocationInvestment(BaseInvestment):
    """资金分配投资记录（实际股数，含费用）"""
    # CA 特有字段（所有字段都需要默认值，因为继承的父类最后字段有默认值）
    shares: int = 0
    avg_cost: float = 0.0  # 平均成本（含交易成本）
    commission: float = 0.0
    stamp_duty: float = 0.0
    transfer_fee: float = 0.0
    total_cost: float = 0.0  # 总成本（含所有费用）
    realized_pnl: float = 0.0  # 已实现盈亏
    
    # 交易记录
    buy_trade: Optional[Trade] = None
    sell_trades: List[Trade] = field(default_factory=list)
    
    @classmethod
    def from_trades(
        cls,
        buy_trade: Trade,
        sell_trades: List[Trade],
        stock_name: str = ""
    ) -> "CapitalAllocationInvestment":
        """
        从交易记录创建 CapitalAllocationInvestment
        
        Args:
            buy_trade: 买入交易
            sell_trades: 卖出交易列表
            stock_name: 股票名称（可选）
        """
        if not buy_trade.is_buy():
            raise ValueError("buy_trade must be a buy trade")
        
        # 计算总成本
        total_cost = buy_trade.total_cost or (buy_trade.amount + buy_trade.fees)
        
        # 计算平均成本
        avg_cost = total_cost / buy_trade.shares if buy_trade.shares > 0 else 0.0
        
        # 计算总费用
        commission = buy_trade.fees  # 简化：假设费用都是佣金
        stamp_duty = 0.0  # 卖出时计算
        transfer_fee = 0.0
        
        # 计算已实现盈亏
        realized_pnl = sum(t.pnl or 0.0 for t in sell_trades if t.pnl is not None)
        
        # 计算总盈亏（已实现 + 未实现）
        # 未实现盈亏需要当前价格，这里只计算已实现
        profit = realized_pnl
        
        # 计算收益率
        roi = (profit / total_cost) if total_cost > 0 else 0.0
        
        # 计算持仓天数
        holding_days = 0
        if buy_trade.date and sell_trades:
            last_sell = max(sell_trades, key=lambda t: t.date)
            try:
                from core.modules.strategy.components.price_factor_simulator.helpers import parse_yyyymmdd
                start_dt = parse_yyyymmdd(buy_trade.date)
                end_dt = parse_yyyymmdd(last_sell.date)
                if start_dt and end_dt:
                    holding_days = max((end_dt - start_dt).days, 1)
            except Exception:
                pass
        
        # 确定状态
        if not sell_trades:
            status = "open"
        elif all(t.shares == 0 for t in sell_trades):  # 全部卖出
            status = "win" if profit > 0 else ("loss" if profit < 0 else "closed")
        else:
            status = "open"  # 部分卖出
        
        # 生成 investment_id
        investment_id = f"ca_{buy_trade.opportunity_id}_{buy_trade.date}"
        
        # 获取卖出价格（最后一次卖出）
        sell_price = None
        sell_date = None
        if sell_trades:
            last_sell = max(sell_trades, key=lambda t: t.date)
            sell_price = last_sell.price
            sell_date = last_sell.date
        
        return cls(
            investment_id=investment_id,
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
            stamp_duty=stamp_duty,
            transfer_fee=transfer_fee,
            total_cost=total_cost,
            realized_pnl=realized_pnl,
            buy_trade=buy_trade,
            sell_trades=sell_trades,
        )
    
    @classmethod
    def from_source(cls, source: Any) -> "CapitalAllocationInvestment":
        """从源数据创建（兼容接口）"""
        if isinstance(source, dict):
            buy_trade_data = source.get("buy_trade")
            sell_trades_data = source.get("sell_trades", [])
            stock_name = source.get("stock_name", "")
            
            buy_trade = Trade.from_dict(buy_trade_data) if buy_trade_data else None
            sell_trades = [Trade.from_dict(t) for t in sell_trades_data] if sell_trades_data else []
            
            if buy_trade:
                return cls.from_trades(buy_trade, sell_trades, stock_name)
        raise ValueError(f"Unsupported source type: {type(source)}")
