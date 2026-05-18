#!/usr/bin/env python3
"""amplitude_limit 专用辅助（如涨跌停价舍入）。"""

from __future__ import annotations

from typing import Tuple


def round_limit_price(price: float, decimals: int) -> float:
    return round(float(price), max(int(decimals), 0))


def compute_limit_prices_from_ratio(
    prev_close: float,
    ratio: float,
    *,
    decimals: int = 2,
) -> Tuple[float, float]:
    base = float(prev_close or 0.0)
    if base <= 0:
        return 0.0, 0.0
    r = float(ratio)
    limit_up = round_limit_price(base * (1.0 + r), decimals)
    limit_down = round_limit_price(base * (1.0 - r), decimals)
    return limit_up, limit_down


__all__ = ["compute_limit_prices_from_ratio", "round_limit_price"]
