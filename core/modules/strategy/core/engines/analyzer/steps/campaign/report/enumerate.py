"""枚举层战役报告（sea）。"""
from __future__ import annotations

from core.modules.strategy.core.enums import SimulateKind

from .base import ReportBase


class EnumerateReport(ReportBase):
    LAYER = "enumerate"
    KIND = SimulateKind.ENUMERATE
