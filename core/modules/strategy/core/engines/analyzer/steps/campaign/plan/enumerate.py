"""机会盘点层战役计划（sea）。"""
from __future__ import annotations

from core.modules.strategy.core.enums import SimulateKind

from .base import AttributionPlanBase


class EnumerateAttributionPlan(AttributionPlanBase):
    """机会盘点层计划。近邻间隔不另开版本。"""

    LAYER = "enum"
    KIND = SimulateKind.ENUMERATE

    @classmethod
    def _skip_price_replay_axes(cls) -> bool:
        """近邻间隔不改变机会，枚举战役不为其另开版本。"""
        return True
