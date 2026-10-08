"""战役总结步：attribute 结果 → headline / highlights / hints。

pipeline 只调 ``SummarizeStep.run(..., layer=)``；层差异在子类。
"""
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Sequence, Type

from ..layers import pick_layer
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
        """按层返回总结类。"""
        return pick_layer(_BY_LAYER, layer, PortfolioSummarize)

    @classmethod
    def run(
        cls,
        attributed: Mapping[str, Any],
        *,
        layer: str = "",
        folder: Any = None,
        gathered: Optional[Mapping[str, Any]] = None,
        executed: Optional[Mapping[str, Any]] = None,
        joint_groups: Sequence[Sequence[str]] = (),
    ) -> Dict[str, Any]:
        """生成本层总结。"""
        return cls.for_layer(layer).run(
            attributed,
            layer=layer,
            folder=folder,
            gathered=gathered,
            executed=executed,
            joint_groups=joint_groups,
        )


__all__ = [
    "EnumerateSummarize",
    "PortfolioSummarize",
    "PriceSummarize",
    "SummarizeBase",
    "SummarizeStep",
]
