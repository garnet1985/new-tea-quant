"""战役收集步：已执行格子 → N 行摘要表。

pipeline 只调 ``GatherStep.run(..., layer=)``；层差异在子类（旋钮过滤）。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Sequence, Type

from core.modules.strategy.core.enums import SimulateKind

from ..layers import declare_layer, pick_layer
from ..plan import AttributionTask
from .base import GatherBase, attach_enum_exit_ratios, compact_summary
from .enum_exits import (
    after_take_profit_probe,
    baseline_exit_diagnosis,
    exit_ratios_for_version,
)

EnumerateGather = declare_layer(
    "EnumerateGather", GatherBase, "enum", SimulateKind.ENUMERATE
)
PriceGather = declare_layer(
    "PriceGather", GatherBase, "price", SimulateKind.PRICE_FACTOR
)
PortfolioGather = declare_layer(
    "PortfolioGather", GatherBase, "portfolio", SimulateKind.PORTFOLIO
)

_BY_LAYER: dict[str, Type[GatherBase]] = {
    "enum": EnumerateGather,
    "price": PriceGather,
    "portfolio": PortfolioGather,
}


class GatherStep:
    """收集步门面：按层分发到对应收集类。"""

    @classmethod
    def for_layer(cls, layer: Any) -> Type[GatherBase]:
        """按层返回收集类。"""
        return pick_layer(_BY_LAYER, layer, PortfolioGather)

    @classmethod
    def run(
        cls,
        folder: Path,
        tasks: Sequence[AttributionTask],
        executed: Mapping[str, Any],
        *,
        layer: str = "",
    ) -> Dict[str, Any]:
        """把该层已执行格子收成表。"""
        focus = layer
        if not focus and tasks:
            focus = str(getattr(tasks[0].kind, "value", tasks[0].kind) or "")
        return cls.for_layer(focus).run(folder, tasks, executed)


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
]
