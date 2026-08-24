"""回测归因：收集 input → analysis/source.json。"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .pipeline import AnalyzerPipeline

__all__ = ["AnalyzerPipeline"]


def __getattr__(name: str):
    if name == "AnalyzerPipeline":
        from .pipeline import AnalyzerPipeline

        return AnalyzerPipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
