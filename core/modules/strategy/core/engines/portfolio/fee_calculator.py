"""Portfolio 成交费用计算。

本文件:
- FeeCalculator: 佣金 / 印花税 / 过户费；buy_total_cost / sell_net_proceeds
  边界: 负责费率数学；不负责 settings 校验或账户状态更新
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional, Union

from core.modules.strategy.core.engines.shared.services.strategy_settings.fees_settings import (
    FeesSettings,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)


@dataclass(frozen=True)
class FeeCalculator:
    """成交费用：佣金 + 过户费；卖出另加印花税。"""

    commission_rate: float = 0.0003
    min_commission: float = 5.0
    stamp_duty_rate: float = 0.001
    transfer_fee_rate: float = 0.00001

    @classmethod
    def from_fees(
        cls,
        fees: Optional[Union[FeesSettings, StrategySettings, Dict[str, Any]]] = None,
    ) -> "FeeCalculator":
        """从 ``FeesSettings`` / ``StrategySettings`` / raw fees dict 构建。"""
        raw: Dict[str, Any]
        if fees is None:
            raw = {}
        elif isinstance(fees, StrategySettings):
            raw = fees.fees.fees
        elif isinstance(fees, FeesSettings):
            raw = fees.fees
        elif isinstance(fees, dict):
            raw = fees
        else:
            raw = {}
        return cls(
            commission_rate=float(raw.get("commission_rate", 0.0003) or 0.0003),
            min_commission=float(raw.get("min_commission", 5.0) or 5.0),
            stamp_duty_rate=float(raw.get("stamp_duty_rate", 0.001) or 0.001),
            transfer_fee_rate=float(raw.get("transfer_fee_rate", 0.00001) or 0.00001),
        )

    def calculate_fees(self, amount: float, side: Literal["buy", "sell"]) -> float:
        amt = max(float(amount or 0.0), 0.0)
        commission = max(amt * self.commission_rate, self.min_commission)
        fees = commission + amt * self.transfer_fee_rate
        if side == "sell":
            fees += amt * self.stamp_duty_rate
        return float(fees)

    def buy_total_cost(self, amount: float) -> float:
        return float(amount) + self.calculate_fees(amount, "buy")

    def sell_net_proceeds(self, amount: float) -> float:
        return float(amount) - self.calculate_fees(amount, "sell")


__all__ = ["FeeCalculator"]
