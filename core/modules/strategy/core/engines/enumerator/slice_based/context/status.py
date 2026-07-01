"""slice_based 模式 runtime status。"""
from __future__ import annotations

from dataclasses import dataclass

from core.modules.strategy.core.engines.enumerator.shared.runtime import RuntimeStatus


@dataclass
class SliceBasedRuntimeStatus(RuntimeStatus):
    """slice_based 模式专用 RuntimeStatus。"""


__all__ = ["SliceBasedRuntimeStatus"]
