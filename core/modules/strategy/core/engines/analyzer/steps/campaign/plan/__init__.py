"""战役计划步：配置 → 格子 / 任务。

pipeline 只调 ``AttributionPlan.plan_from_folder(..., layer=)``；层差异在子类。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, List, Type

from core.modules.strategy.core.enums import SimulateKind

from ..config import AttributionConfigBase
from ..layers import declare_layer, pick_layer
from .base import AttributionPlanBase
from .enumerate import EnumerateAttributionPlan
from .models import (
    AttributionCell,
    AttributionTask,
    ParameterPlan,
    cell_identity,
    simulate_steps_for_kind,
)
from .portfolio import PortfolioAttributionPlan

PriceAttributionPlan = declare_layer(
    "PriceAttributionPlan",
    AttributionPlanBase,
    "price_factor",
    SimulateKind.PRICE_FACTOR,
)

_BY_LAYER: dict[str, Type[AttributionPlanBase]] = {
    EnumerateAttributionPlan.LAYER: EnumerateAttributionPlan,
    "price_factor": PriceAttributionPlan,
    PortfolioAttributionPlan.LAYER: PortfolioAttributionPlan,
}


class AttributionPlan:
    """计划步门面：按层分发到对应计划类。"""

    @classmethod
    def for_layer(cls, layer: Any) -> Type[AttributionPlanBase]:
        return pick_layer(_BY_LAYER, layer, PortfolioAttributionPlan)

    @classmethod
    def plan_from_folder(
        cls,
        folder: Path,
        config: AttributionConfigBase,
        *,
        layer: str = "",
    ) -> ParameterPlan:
        return cls.for_layer(layer or config.layer).plan_from_folder(folder, config)

    @classmethod
    def expand_from_folder(
        cls,
        folder: Path,
        config: AttributionConfigBase,
        *,
        layer: str = "",
    ) -> List[AttributionCell]:
        return cls.for_layer(layer or config.layer).expand_from_folder(folder, config)

    @classmethod
    def plan(cls, snapshot, config: AttributionConfigBase, *, layer: str = ""):
        return cls.for_layer(layer or config.layer).plan(snapshot, config)

    @classmethod
    def expand(cls, snapshot, config: AttributionConfigBase, *, layer: str = ""):
        return cls.for_layer(layer or config.layer).expand(snapshot, config)


__all__ = [
    "AttributionCell",
    "AttributionPlan",
    "AttributionPlanBase",
    "AttributionTask",
    "EnumerateAttributionPlan",
    "ParameterPlan",
    "PortfolioAttributionPlan",
    "PriceAttributionPlan",
    "cell_identity",
    "simulate_steps_for_kind",
]
