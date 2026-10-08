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


@dataclass(frozen=True)
class ParameterPlan:
    """按层 inputs 展开后的格子。"""

    cells: Tuple[AttributionCell, ...] = ()
    cost_warning: str = ""

    def families(self) -> List[Tuple[str, List[AttributionCell]]]:
        """按家族列出格子。"""
        if not self.cells:
            return []
        name = self.cells[0].family or "oaat"
        return [(name, list(self.cells))]

    def execute_source_cells(self) -> List[AttributionCell]:
        """返回真正要执行的格子。"""
        return list(self.cells)

    def listed_cells(self) -> List[AttributionCell]:
        """返回计划里列出的全部格子。"""
        return list(self.execute_source_cells())


def cell_identity(cell: AttributionCell) -> str:
    """回测身份：用 execute_settings。"""
    return json.dumps(
        cell.execute_settings,
        sort_keys=True,
        default=str,
        ensure_ascii=False,
    )


def simulate_steps_for_kind(kind: SimulateKind) -> Tuple[SimulateKind, ...]:
    """本层 CLI 要补齐的产物链：只到目标层，上游缺则先补（懒执行）。

    ``sea`` → 仅枚举；``spa`` → 枚举+价格；``soa`` → 枚举+价格+组合。
    """
    if kind == SimulateKind.ENUMERATE:
        return (SimulateKind.ENUMERATE,)
    if kind == SimulateKind.PRICE_FACTOR:
        return (SimulateKind.ENUMERATE, SimulateKind.PRICE_FACTOR)
    if kind == SimulateKind.PORTFOLIO:
        return (
            SimulateKind.ENUMERATE,
            SimulateKind.PRICE_FACTOR,
            SimulateKind.PORTFOLIO,
        )
    return (kind,)


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
        """由格子生成执行任务。"""
        steps = simulate_steps_for_kind(kind)
        return [cls(cell=cell, kind=kind, steps=steps) for cell in cells]
