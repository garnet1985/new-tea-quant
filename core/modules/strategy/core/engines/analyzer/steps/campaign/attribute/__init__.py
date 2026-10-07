"""战役归因入口：按层分发到各自归因步骤。"""
from __future__ import annotations

from typing import Any, Dict, Mapping, Type

from ..layers import pick_layer
from .base import AttributeBase
from .enumerate import EnumerateAttributeStep
from .portfolio import PortfolioAttributeStep
from .price import PriceAttributeStep

_BY_LAYER: Dict[str, Type[AttributeBase]] = {
    EnumerateAttributeStep.LAYER: EnumerateAttributeStep,
    PriceAttributeStep.LAYER: PriceAttributeStep,
    PortfolioAttributeStep.LAYER: PortfolioAttributeStep,
}


class AttributeStep:
    """兼容门面：``run(..., layer=)`` → 对应层归因器。"""

    @classmethod
    def for_layer(cls, layer: Any) -> Type[AttributeBase]:
        return pick_layer(_BY_LAYER, layer, PortfolioAttributeStep)

    @classmethod
    def run(
        cls,
        gathered: Mapping[str, Any],
        *,
        layer: str = "",
    ) -> Dict[str, Any]:
        return cls.for_layer(layer).run(gathered)


__all__ = [
    "AttributeBase",
    "AttributeStep",
    "EnumerateAttributeStep",
    "PriceAttributeStep",
    "PortfolioAttributeStep",
]
