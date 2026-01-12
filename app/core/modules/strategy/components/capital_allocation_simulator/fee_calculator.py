#!/usr/bin/env python3
"""
交易费用计算模块

负责计算买入和卖出的交易成本
"""

from typing import Literal


class FeeCalculator:
    """交易费用计算器"""

    def __init__(
        self,
        commission_rate: float,
        min_commission: float,
        stamp_duty_rate: float,
        transfer_fee_rate: float,
    ):
        """
        初始化费用计算器
        
        Args:
            commission_rate: 佣金率（双边，例如 0.00025 表示万2.5）
            min_commission: 最低佣金（元）
            stamp_duty_rate: 印花税率（卖出时，例如 0.001 表示千1）
            transfer_fee_rate: 过户费（如需要）
        """
        self.commission_rate = commission_rate
        self.min_commission = min_commission
        self.stamp_duty_rate = stamp_duty_rate
        self.transfer_fee_rate = transfer_fee_rate

    def calculate_fees(
        self,
        amount: float,
        side: Literal["buy", "sell"],
    ) -> float:
        """
        计算交易费用
        
        Args:
            amount: 交易金额（不含费用）
            side: 交易方向（"buy" 或 "sell"）
            
        Returns:
            总费用（元）
        """
        fees = 0.0

        # 佣金（买入和卖出都有）
        commission = amount * self.commission_rate
        commission = max(commission, self.min_commission)
        fees += commission

        # 印花税（仅卖出时）
        if side == "sell":
            fees += amount * self.stamp_duty_rate

        # 过户费（如需要）
        fees += amount * self.transfer_fee_rate

        return fees

    def calculate_total_cost(self, amount: float, side: Literal["buy", "sell"]) -> float:
        """
        计算总成本（含费用）
        
        Args:
            amount: 交易金额（不含费用）
            side: 交易方向
            
        Returns:
            总成本（买入时）或净收入（卖出时）
        """
        fees = self.calculate_fees(amount, side)
        if side == "buy":
            return amount + fees  # 买入：总成本 = 金额 + 费用
        else:
            return amount - fees  # 卖出：净收入 = 金额 - 费用
