"""战役格子与任务模型。"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.enums import SimulateKind


@dataclass(frozen=True)
class AttributionCell:
    """战役一格：目标身份，还不是一次 Run。"""

    index: int
    overlay: Dict[str, Any]
    runtime_settings: Dict[str, Any]
    execute_settings: Dict[str, Any]
    effective: Optional[StrategySettings] = None
    version_id: Optional[int] = None
    family: str = ""

    @property
    def is_select(self) -> bool:
        return self.version_id is not None


@dataclass(frozen=True)
class ParameterPlan:
    """选号或按层 inputs 展开后的格子。"""

    cells: Tuple[AttributionCell, ...] = ()
    selected: Tuple[AttributionCell, ...] = ()
    cost_warning: str = ""

    def families(self) -> List[Tuple[str, List[AttributionCell]]]:
        out: List[Tuple[str, List[AttributionCell]]] = []
        if self.selected:
            out.append(("select", list(self.selected)))
        if self.cells:
            name = self.cells[0].family or "inputs"
            out.append((name, list(self.cells)))
        return out

    def execute_source_cells(self) -> List[AttributionCell]:
        if self.selected:
            return list(self.selected)
        return list(self.cells)

    def listed_cells(self) -> List[AttributionCell]:
        return list(self.execute_source_cells())


def cell_identity(cell: AttributionCell) -> str:
    """回测身份：选号用 version；其余用 execute_settings。"""
    if cell.is_select:
        return f"select:{cell.version_id}"
    return json.dumps(
        cell.execute_settings,
        sort_keys=True,
        default=str,
        ensure_ascii=False,
    )


@dataclass(frozen=True)
class AttributionTask:
    """一格对应的可执行任务（交给 ``Strategy.simulate`` 或按号读取）。"""

    cell: AttributionCell
    kind: SimulateKind
    steps: Tuple[SimulateKind, ...] = ()

    @classmethod
    def from_cells(
        cls,
        cells: Sequence[AttributionCell],
        *,
        kind: SimulateKind,
    ) -> List["AttributionTask"]:
        steps = (kind,)
        return [cls(cell=cell, kind=kind, steps=steps) for cell in cells]
