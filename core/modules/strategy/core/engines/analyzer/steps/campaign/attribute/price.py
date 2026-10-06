"""价格层战役归因：代表样本边与结实程度；共用副本上的想法/去噪轴。"""
from __future__ import annotations

from .base import AttributeBase


class PriceAttributeStep(AttributeBase):
    """spa：问去近邻后的 ROI / 胜率 / 利润是否普遍。

    格子身份与 sea/soa 共用；报告可对照 core/goal/simulation，不含组合槽位。
    """

    LAYER = "price_factor"
    KNOB_PREFIXES = ("core.", "goal.", "simulation.")
    OUTCOMES = (
        ("price_factor", "avg_roi"),
        ("price_factor", "win_rate"),
        ("price_factor", "total_profit"),
        ("price_factor", "payoff_ratio"),
        ("price_factor", "roi_p50"),
        ("price_factor", "top5_trade_profit_share"),
        ("price_factor", "top5_stock_profit_share"),
        ("price_factor", "avg_roi_without_top5"),
        ("price_factor", "take_profit_profit_share"),
        ("price_factor", "stop_loss_profit_share"),
        ("price_factor", "expire_profit_share"),
    )


__all__ = ["PriceAttributeStep"]
