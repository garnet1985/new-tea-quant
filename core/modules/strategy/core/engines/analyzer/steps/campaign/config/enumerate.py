"""枚举层战役配置（sea）。"""
from __future__ import annotations

from core.modules.strategy.core.enums import SimulateKind

from .base import AttributionConfigBase


class EnumerateAttributionConfig(AttributionConfigBase):
    """sea：只关心机会与 goal 纸面相关的对照声明。"""

    LAYER = "enumerate"
    KIND = SimulateKind.ENUMERATE
