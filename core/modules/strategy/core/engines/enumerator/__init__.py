"""枚举器统一编排入口（lazy — 避免 contracts ↔ pipeline 循环 import）。"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .pipeline import EnumeratorPipeline

__all__ = ["EnumeratorPipeline"]


def __getattr__(name: str):
    if name == "EnumeratorPipeline":
        from .pipeline import EnumeratorPipeline

        return EnumeratorPipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
