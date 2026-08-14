"""价格因子引擎（lazy — 避免 contracts ↔ pipeline 循环 import）。"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .pipeline import PriceFactorPipeline

__all__ = ["PriceFactorPipeline"]


def __getattr__(name: str):
    if name == "PriceFactorPipeline":
        from .pipeline import PriceFactorPipeline

        return PriceFactorPipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
