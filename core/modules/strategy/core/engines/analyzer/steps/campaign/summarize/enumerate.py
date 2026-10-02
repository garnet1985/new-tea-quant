"""枚举层战役总结（sea）。"""
from __future__ import annotations

from core.modules.strategy.core.enums import SimulateKind

from .base import SummarizeBase


class EnumerateSummarize(SummarizeBase):
    LAYER = "enumerate"
    KIND = SimulateKind.ENUMERATE
