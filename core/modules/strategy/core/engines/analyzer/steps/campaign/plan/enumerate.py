"""枚举层战役计划（sea）。"""
from __future__ import annotations

from core.modules.strategy.core.enums import SimulateKind

from .base import AttributionPlanBase


class EnumerateAttributionPlan(AttributionPlanBase):
    LAYER = "enumerate"
    KIND = SimulateKind.ENUMERATE
