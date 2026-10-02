"""组合层战役落盘（soa）。"""
from __future__ import annotations

from core.modules.strategy.core.enums import SimulateKind

from .base import PersistBase


class PortfolioPersist(PersistBase):
    LAYER = "portfolio"
    KIND = SimulateKind.PORTFOLIO
    TASK_ID = "portfolio"
