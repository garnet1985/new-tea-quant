"""价格层战役归因：代表样本边与结实程度；共用副本上的想法/去噪轴。"""
from __future__ import annotations

from .base import AttributeBase


class PriceAttributeStep(AttributeBase):
    """看去噪后的收益和利润是否普遍。不含组合槽位。"""

    LAYER = "price"
    KNOB_PREFIXES = ("core.", "goal.", "simulation.")
    OUTCOMES = (
        ("price", "avg_roi"),
        ("price", "win_rate"),
        ("price", "total_profit"),
        ("price", "payoff_ratio"),
        ("price", "roi_p50"),
        ("price", "top5_trade_profit_share"),
        ("price", "top5_stock_profit_share"),
        ("price", "avg_roi_without_top5"),
        ("price", "take_profit_profit_share"),
        ("price", "stop_loss_profit_share"),
        ("price", "expire_profit_share"),
    )


__all__ = ["PriceAttributeStep"]
