#!/usr/bin/env python3
from typing import Literal


class FeeCalculator:
    def __init__(
        self,
        commission_rate: float,
        min_commission: float,
        stamp_duty_rate: float,
        transfer_fee_rate: float,
    ):
        self.commission_rate = commission_rate
        self.min_commission = min_commission
        self.stamp_duty_rate = stamp_duty_rate
        self.transfer_fee_rate = transfer_fee_rate

    def calculate_fees(self, amount: float, side: Literal["buy", "sell"]) -> float:
        commission = max(amount * self.commission_rate, self.min_commission)
        fees = commission + amount * self.transfer_fee_rate
        if side == "sell":
            fees += amount * self.stamp_duty_rate
        return fees

    def calculate_total_cost(self, amount: float, side: Literal["buy", "sell"]) -> float:
        fees = self.calculate_fees(amount, side)
        return amount + fees if side == "buy" else amount - fees


__all__ = ["FeeCalculator"]
