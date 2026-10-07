"""战役执行步：格子 → simulate / 选号读取。

pipeline 只调 ``ExecuteStep.run(..., kind=)``；层差异在子类。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Type

from core.modules.strategy.core.enums import SimulateKind

from ..layers import declare_layer, pick_layer
from ..plan import AttributionCell, AttributionTask
from .base import ExecuteBase
from .models import CellExecuteResult

EnumerateExecute = declare_layer(
    "EnumerateExecute", ExecuteBase, "enumerate", SimulateKind.ENUMERATE
)
PriceExecute = declare_layer(
    "PriceExecute", ExecuteBase, "price_factor", SimulateKind.PRICE_FACTOR
)
PortfolioExecute = declare_layer(
    "PortfolioExecute", ExecuteBase, "portfolio", SimulateKind.PORTFOLIO
)

_BY_LAYER: dict[str, Type[ExecuteBase]] = {
    "enumerate": EnumerateExecute,
    "price_factor": PriceExecute,
    "portfolio": PortfolioExecute,
}


class ExecuteStep(ExecuteBase):
    """执行步门面：按层分发到对应执行类。"""

    @classmethod
    def for_layer(cls, layer: Any) -> Type[ExecuteBase]:
        """按层返回执行类。"""
        return pick_layer(_BY_LAYER, layer, PortfolioExecute)

    @classmethod
    def run(
        cls,
        folder: Path,
        tasks: Sequence[AttributionTask],
        *,
        kind: Optional[SimulateKind] = None,
        ignore_cache: bool = False,
    ) -> Dict[str, Any]:
        """执行该层的格子。"""
        layer = kind if kind is not None else cls.KIND
        return cls.for_layer(layer).run(
            folder, tasks, kind=layer, ignore_cache=ignore_cache
        )

    @classmethod
    def unique_tasks(
        cls, tasks: Sequence[AttributionTask]
    ) -> List[AttributionTask]:
        """按执行身份去掉重复任务。"""
        return ExecuteBase.unique_tasks(tasks)

    @classmethod
    def bind(
        cls,
        executed: Mapping[str, Any],
        unique_cells: Sequence[AttributionCell],
        family_cells: Sequence[AttributionCell],
    ) -> Dict[str, Any]:
        """把去重后的结果领回各家族的行。"""
        return ExecuteBase.bind(executed, unique_cells, family_cells)


__all__ = [
    "CellExecuteResult",
    "EnumerateExecute",
    "ExecuteBase",
    "ExecuteStep",
    "PortfolioExecute",
    "PriceExecute",
]
