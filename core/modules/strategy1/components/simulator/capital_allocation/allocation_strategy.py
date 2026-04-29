#!/usr/bin/env python3
"""
资金分配策略模块

实现 equal_capital、equal_shares、kelly 三种分配模式
"""

from typing import Dict, Any, Optional, Literal
from core.modules.strategy.models.account import Account
from .fee_calculator import FeeCalculator


class AllocationStrategy:
    """资金分配策略"""

    def __init__(
        self,
        mode: Literal["equal_capital", "equal_shares", "kelly"],
        initial_capital: float,
        max_portfolio_size: int,
        lot_size: int = 100,
        lots_per_trade: int = 1,
        kelly_fraction: float = 0.5,
        fee_calculator: Optional[FeeCalculator] = None,
    ):
        """
        初始化分配策略
        
        Args:
            mode: 分配模式
            initial_capital: 初始资金
            max_portfolio_size: 最大组合持仓数
            lot_size: 1手对应的股票数（A股通常是100股）
            lots_per_trade: 每次买入的手数（equal_shares 模式）
            kelly_fraction: Kelly 仓位折扣比例（kelly 模式）
            fee_calculator: 费用计算器
        """
        self.mode = mode
        self.initial_capital = initial_capital
        self.max_portfolio_size = max_portfolio_size
        self.lot_size = lot_size
        self.lots_per_trade = lots_per_trade
        self.kelly_fraction = kelly_fraction
        self.fee_calculator = fee_calculator

        # equal_capital 模式下，每笔交易的目标资金
        self.per_trade_capital = initial_capital / max_portfolio_size

    def calculate_shares_to_buy(
        self,
        account: Account,
        trigger_price: float,
        win_rate: Optional[float] = None,
    ) -> int:
        """
        计算应该买入的股数
        
        Args:
            account: 账户信息
            trigger_price: 触发价格
            win_rate: 胜率（kelly 模式需要，可选）
            
        Returns:
            应该买入的股数（0 表示不买入或无法买入）
        """
        if self.mode == "equal_capital":
            return self._calculate_equal_capital(account, trigger_price)
        elif self.mode == "equal_shares":
            return self._calculate_equal_shares(account, trigger_price)
        elif self.mode == "kelly":
            return self._calculate_kelly(account, trigger_price, win_rate)
        else:
            return 0

    def _calculate_equal_capital(
        self,
        account: Account,
        trigger_price: float,
    ) -> int:
        """等资金投入模式"""
        # 检查现金是否足够
        if account.cash < self.per_trade_capital:
            return 0

        # 使用 per_trade_capital 计算应该买入的股数（而不是使用全部现金）
        # 计算最大可买股数（向下取整到 lot_size 的倍数）
        max_shares = int(self.per_trade_capital / trigger_price)
        lots = max_shares // self.lot_size
        buy_shares = lots * self.lot_size

        if buy_shares == 0:
            return 0

        # 计算实际成本（含费用）
        gross_amount = buy_shares * trigger_price
        if self.fee_calculator:
            total_cost = self.fee_calculator.calculate_total_cost(
                gross_amount, "buy"
            )
        else:
            total_cost = gross_amount

        # 如果现金不足以支付总成本，减少股数
        if account.cash < total_cost:
            # 重新计算，考虑费用，但不超过 per_trade_capital
            available_capital = min(account.cash, self.per_trade_capital)
            max_affordable_shares = int(
                (available_capital / (trigger_price * (1 + self.fee_calculator.commission_rate)))
                if self.fee_calculator
                else (available_capital / trigger_price)
            )
            lots = max_affordable_shares // self.lot_size
            buy_shares = lots * self.lot_size

        return buy_shares

    def _calculate_equal_shares(
        self,
        account: Account,
        trigger_price: float,
    ) -> int:
        """等股投入模式"""
        target_shares = self.lot_size * self.lots_per_trade

        # 计算总成本（含费用）
        gross_amount = target_shares * trigger_price
        if self.fee_calculator:
            total_cost = self.fee_calculator.calculate_total_cost(gross_amount, "buy")
        else:
            total_cost = gross_amount

        # 检查现金是否足够
        if account.cash < total_cost:
            return 0

        return target_shares

    def _calculate_kelly(
        self,
        account: Account,
        trigger_price: float,
        win_rate: Optional[float] = None,
    ) -> int:
        """Kelly 公式模式"""
        if win_rate is None:
            # 如果没有提供胜率，默认不参与
            return 0

        # 简化版 Kelly 公式：f_raw = 2 * p - 1
        f_raw = 2 * win_rate - 1

        # 如果胜率 <= 50%，不参与
        if f_raw <= 0:
            return 0

        # 保守控制：f = max(0, f_raw) / kelly_divisor
        # 这里 kelly_divisor = 1 / kelly_fraction
        kelly_divisor = 1.0 / self.kelly_fraction if self.kelly_fraction > 0 else 1.0
        f = f_raw / kelly_divisor

        # 目标资金
        target_capital = f * account.cash

        # 计算股数（向下取整到 lot_size 的倍数）
        max_shares = int(target_capital / trigger_price)
        lots = max_shares // self.lot_size
        buy_shares = lots * self.lot_size

        if buy_shares == 0:
            return 0

        # 计算实际成本（含费用）
        gross_amount = buy_shares * trigger_price
        if self.fee_calculator:
            total_cost = self.fee_calculator.calculate_total_cost(gross_amount, "buy")
        else:
            total_cost = gross_amount

        # 如果现金不足以支付总成本，减少股数
        if account.cash < total_cost:
            max_affordable_shares = int(
                (account.cash / (trigger_price * (1 + self.fee_calculator.commission_rate)))
                if self.fee_calculator
                else (account.cash / trigger_price)
            )
            lots = max_affordable_shares // self.lot_size
            buy_shares = lots * self.lot_size

        return buy_shares

