"""后复权 ROI 与同股市值（strategy 回测层只准这一处算术）。

消费者: enumerator / Investment、price_factor、portfolio 盯市与成交、decision_maker holdings

本文件:
- HfqRoi: PRICE_LAYERS 的 100→120
  边界: 不算手续费；不做 K 线 IO；current_hfq<=0 视为缺价（ROI=0），不是腰斩
  触发用价格比较（is_target_hit），避免 (现/入−1) 在精确档位上的浮点漏触发
"""

from __future__ import annotations

import math
from typing import Any


class HfqRoi:
    """后复权 ROI、档位价、同股等价市值。"""

    @staticmethod
    def to_finite(value: Any) -> float:
        """非法或非有限数视为 0。"""
        try:
            number = float(value)
        except (TypeError, ValueError):
            return 0.0
        if not math.isfinite(number):
            return 0.0
        return number

    @staticmethod
    def ratio(entry_hfq: Any, current_hfq: Any) -> float:
        """ROI = (现 hfq − 入场 hfq) / 入场 hfq。分母或现价不合法则 0。"""
        entry = HfqRoi.to_finite(entry_hfq)
        current = HfqRoi.to_finite(current_hfq)
        if entry <= 0 or current <= 0:
            return 0.0
        return current / entry - 1.0

    @staticmethod
    def target_price(entry_hfq: Any, ratio: Any) -> float:
        """档位价 = 入场 hfq × (1+ratio)。入场不合法则 0。"""
        entry = HfqRoi.to_finite(entry_hfq)
        if entry <= 0:
            return 0.0
        return entry * (1.0 + HfqRoi.to_finite(ratio))

    @staticmethod
    def is_target_hit(entry_hfq: Any, current_hfq: Any, ratio: Any) -> bool:
        """是否达到 ``entry × (1+ratio)``。``ratio>0`` 向上，``ratio<=0`` 向下（含回落到成本）。"""
        current = HfqRoi.to_finite(current_hfq)
        target = HfqRoi.target_price(entry_hfq, ratio)
        if current <= 0 or target <= 0:
            return False
        if HfqRoi.to_finite(ratio) > 0:
            return current >= target
        return current <= target

    @staticmethod
    def cash_profit(shares: Any, entry_raw: Any, roi: Any) -> float:
        """盈利(元) = 买入股数 × 买入 raw × ROI（不含 fees）。"""
        return (
            HfqRoi.to_finite(shares)
            * HfqRoi.to_finite(entry_raw)
            * HfqRoi.to_finite(roi)
        )

    @staticmethod
    def mark_value(shares: Any, entry_raw: Any, roi: Any) -> float:
        """同股等价市值 = 本金 + 盈利；不是交易所打印价 × 股数。"""
        principal = HfqRoi.to_finite(shares) * HfqRoi.to_finite(entry_raw)
        return principal + HfqRoi.cash_profit(shares, entry_raw, roi)


__all__ = ["HfqRoi"]
