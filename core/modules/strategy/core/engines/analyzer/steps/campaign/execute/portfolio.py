"""组合层战役执行（soa）。"""
from __future__ import annotations

from core.modules.strategy.core.enums import SimulateKind

from .base import ExecuteBase


class PortfolioExecute(ExecuteBase):
    LAYER = "portfolio"
    KIND = SimulateKind.PORTFOLIO
