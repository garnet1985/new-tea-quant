"""枚举层战役收集（sea）。"""
from __future__ import annotations

from core.modules.strategy.core.enums import SimulateKind

from .base import GatherBase


class EnumerateGather(GatherBase):
    LAYER = "enumerate"
    KIND = SimulateKind.ENUMERATE
