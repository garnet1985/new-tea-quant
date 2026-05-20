#!/usr/bin/env python3
"""lot_size 专用辅助（如向下取整买入股数）。"""

from __future__ import annotations


def floor_buy_quantity(shares: int, *, min_lot: int, lot_step: int) -> int:
    qty = int(shares)
    min_l = max(int(min_lot), 1)
    step = max(int(lot_step), 1)
    if qty < min_l:
        return 0
    if step <= 1:
        return qty
    floored = (qty // step) * step
    return floored if floored >= min_l else 0


__all__ = ["floor_buy_quantity"]
