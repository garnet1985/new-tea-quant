"""slice_based 模式 hook data context。"""
from __future__ import annotations

from core.modules.strategy.core.hooks.context import DataContext


class SliceBasedDataContext(DataContext):
    """slice_based 模式专用 DataContext。"""


__all__ = ["SliceBasedDataContext"]
