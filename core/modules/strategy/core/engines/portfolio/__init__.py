"""Portfolio 引擎 — 资金/仓位模拟（lazy — 避免 contracts ↔ pipeline 循环 import）。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .data_class import (
    Account,
    PortfolioEvent,
    PortfolioInvestment,
    Position,
    Trade,
)

if TYPE_CHECKING:
    from .pipeline import PortfolioPipeline

__all__ = [
    "Account",
    "PortfolioEvent",
    "PortfolioInvestment",
    "PortfolioPipeline",
    "Position",
    "Trade",
]


def __getattr__(name: str):
    if name == "PortfolioPipeline":
        from .pipeline import PortfolioPipeline

        return PortfolioPipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
