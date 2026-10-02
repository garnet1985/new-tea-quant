"""战役总结步：attribute 结果 → headline / highlights / hints。

pipeline 只调 ``SummarizeStep.run(..., layer=)``；层差异在子类。
"""
from __future__ import annotations

from typing import Any, Dict, Mapping, Type

from .base import SummarizeBase
from .enumerate import EnumerateSummarize
from .portfolio import PortfolioSummarize
from .price import PriceSummarize

_BY_LAYER: dict[str, Type[SummarizeBase]] = {
    EnumerateSummarize.LAYER: EnumerateSummarize,
    PriceSummarize.LAYER: PriceSummarize,
    PortfolioSummarize.LAYER: PortfolioSummarize,
}


class SummarizeStep:
    """总结步门面：按层分发到对应总结类。"""

    @classmethod
    def for_layer(cls, layer: Any) -> Type[SummarizeBase]:
        focus = str(getattr(layer, "value", layer) or "").strip()
        step = _BY_LAYER.get(focus)
        if step is None:
            return PortfolioSummarize
        return step

    @classmethod
    def run(
        cls,
        attributed: Mapping[str, Any],
        *,
        layer: str = "",
    ) -> Dict[str, Any]:
        return cls.for_layer(layer).run(attributed, layer=layer)


__all__ = [
    "EnumerateSummarize",
    "PortfolioSummarize",
    "PriceSummarize",
    "SummarizeBase",
    "SummarizeStep",
]
