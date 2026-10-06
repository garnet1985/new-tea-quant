"""战役收集步：已执行格子 → N 行摘要表。

pipeline 只调 ``GatherStep.run(..., layer=)``；层差异在子类（旋钮过滤）。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Sequence, Type

from ..plan import AttributionTask
from .base import GatherBase, attach_enum_exit_ratios, compact_summary
from .enum_exits import (
    after_take_profit_probe,
    baseline_exit_diagnosis,
    exit_ratios_for_version,
)
from .enumerate import EnumerateGather
from .portfolio import PortfolioGather
from .price import PriceGather

_BY_LAYER: dict[str, Type[GatherBase]] = {
    EnumerateGather.LAYER: EnumerateGather,
    PriceGather.LAYER: PriceGather,
    PortfolioGather.LAYER: PortfolioGather,
}


class GatherStep:
    """收集步门面：按层分发到对应收集类。"""

    @classmethod
    def for_layer(cls, layer: Any) -> Type[GatherBase]:
        focus = str(getattr(layer, "value", layer) or "").strip()
        step = _BY_LAYER.get(focus)
        if step is None:
            return PortfolioGather
        return step

    @classmethod
    def run(
        cls,
        folder: Path,
        tasks: Sequence[AttributionTask],
        executed: Mapping[str, Any],
        *,
        layer: str = "",
    ) -> Dict[str, Any]:
        focus = layer
        if not focus and tasks:
            focus = str(getattr(tasks[0].kind, "value", tasks[0].kind) or "")
        return cls.for_layer(focus).run(folder, tasks, executed)


# 测试仍可按旧名导入
_compact_summary = compact_summary

__all__ = [
    "EnumerateGather",
    "GatherBase",
    "GatherStep",
    "PortfolioGather",
    "PriceGather",
    "after_take_profit_probe",
    "attach_enum_exit_ratios",
    "baseline_exit_diagnosis",
    "compact_summary",
    "exit_ratios_for_version",
    "_compact_summary",
]
