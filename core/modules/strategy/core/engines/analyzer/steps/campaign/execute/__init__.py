"""战役执行步：格子 → simulate / 选号读取。

pipeline 只调 ``ExecuteStep.run(..., kind=)``；层差异在子类。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Type

from core.modules.strategy.core.enums import SimulateKind

from ..plan import AttributionCell, AttributionTask
from .base import ExecuteBase
from .enumerate import EnumerateExecute
from .models import CellExecuteResult
from .portfolio import PortfolioExecute
from .price import PriceExecute

_BY_LAYER: dict[str, Type[ExecuteBase]] = {
    EnumerateExecute.LAYER: EnumerateExecute,
    PriceExecute.LAYER: PriceExecute,
    PortfolioExecute.LAYER: PortfolioExecute,
}


class ExecuteStep(ExecuteBase):
    """执行步门面：按层分发到对应执行类。"""

    @classmethod
    def for_layer(cls, layer: Any) -> Type[ExecuteBase]:
        focus = str(getattr(layer, "value", layer) or "").strip()
        step = _BY_LAYER.get(focus)
        if step is None:
            return PortfolioExecute
        return step

    @classmethod
    def run(
        cls,
        folder: Path,
        tasks: Sequence[AttributionTask],
        *,
        kind: Optional[SimulateKind] = None,
        ignore_cache: bool = False,
    ) -> Dict[str, Any]:
        layer = kind if kind is not None else cls.KIND
        return cls.for_layer(layer).run(
            folder, tasks, kind=layer, ignore_cache=ignore_cache
        )

    @classmethod
    def unique_tasks(
        cls, tasks: Sequence[AttributionTask]
    ) -> List[AttributionTask]:
        return ExecuteBase.unique_tasks(tasks)

    @classmethod
    def bind(
        cls,
        executed: Mapping[str, Any],
        unique_cells: Sequence[AttributionCell],
        family_cells: Sequence[AttributionCell],
    ) -> Dict[str, Any]:
        return ExecuteBase.bind(executed, unique_cells, family_cells)


__all__ = [
    "CellExecuteResult",
    "EnumerateExecute",
    "ExecuteBase",
    "ExecuteStep",
    "PortfolioExecute",
    "PriceExecute",
]
