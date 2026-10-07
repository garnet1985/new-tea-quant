"""战役落盘步：报告 → ``results/attribution/{n}/{task}/``。

pipeline 只调 ``PersistStep.run(..., layer=)``；层差异在子类（默认 task 目录名）。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Type

from core.modules.strategy.core.enums import SimulateKind

from ..layers import declare_layer, pick_layer
from .base import (
    PARAMETER_TASK_ID,
    ROLLING_TASK_ID,
    PersistBase,
)
from .groups import AttributionGroupStore

EnumeratePersist = declare_layer(
    "EnumeratePersist", PersistBase, "enumerate", SimulateKind.ENUMERATE
)
PricePersist = declare_layer(
    "PricePersist", PersistBase, "price_factor", SimulateKind.PRICE_FACTOR
)
PortfolioPersist = declare_layer(
    "PortfolioPersist", PersistBase, "portfolio", SimulateKind.PORTFOLIO
)

_BY_LAYER: dict[str, Type[PersistBase]] = {
    "enumerate": EnumeratePersist,
    "price_factor": PricePersist,
    "portfolio": PortfolioPersist,
}


class PersistStep:
    """落盘步门面：按层分发到对应落盘类。"""

    @classmethod
    def for_layer(cls, layer: Any) -> Type[PersistBase]:
        return pick_layer(_BY_LAYER, layer, PortfolioPersist)

    @classmethod
    def run(
        cls,
        folder: Path,
        config: Any,
        report: Mapping[str, Any],
        *,
        executed: Optional[Mapping[str, Any]] = None,
        task_id: str = "",
        task_kind: str = "",
        layer: str = "",
    ) -> Dict[str, Any]:
        focus = layer or str(report.get("layer") or report.get("kind") or "")
        return cls.for_layer(focus).run(
            folder,
            config,
            report,
            executed=executed,
            task_id=task_id,
            task_kind=task_kind,
        )


__all__ = [
    "AttributionGroupStore",
    "EnumeratePersist",
    "PARAMETER_TASK_ID",
    "PersistBase",
    "PersistStep",
    "PortfolioPersist",
    "PricePersist",
    "ROLLING_TASK_ID",
]
