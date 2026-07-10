"""枚举器引擎（lazy — 避免 contracts ↔ pipeline 循环 import）。"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .engine import EnumeratorEngine

__all__ = ["EnumeratorEngine"]


def __getattr__(name: str):
    if name == "EnumeratorEngine":
        from .engine import EnumeratorEngine

        return EnumeratorEngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
