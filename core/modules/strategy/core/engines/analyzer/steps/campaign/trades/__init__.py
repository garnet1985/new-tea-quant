"""战役单笔步：价格层机会铺平 → XGB / SHAP。

pipeline 只在 spa 调用 ``TradesStep.run``；其他层返回 skipped。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Type

from ..plan import AttributionCell
from .base import TradesBase
from .enumerate import EnumerateTrades
from .portfolio import PortfolioTrades
from .price import PriceTrades

_BY_LAYER: dict[str, Type[TradesBase]] = {
    EnumerateTrades.LAYER: EnumerateTrades,
    PriceTrades.LAYER: PriceTrades,
    PortfolioTrades.LAYER: PortfolioTrades,
}


class TradesStep:
    """单笔步门面：按层分发（仅 spa 有实质工作）。"""

    @classmethod
    def for_layer(cls, layer: Any) -> Type[TradesBase]:
        focus = str(getattr(layer, "value", layer) or "").strip()
        step = _BY_LAYER.get(focus)
        if step is None:
            return PriceTrades
        return step

    @classmethod
    def run(
        cls,
        folder: Path,
        unique_cells: Sequence[AttributionCell],
        executed: Mapping[str, Any],
        *,
        layer: str = "price_factor",
    ) -> Dict[str, Any]:
        return cls.for_layer(layer).run(folder, unique_cells, executed)

    @classmethod
    def from_rows(
        cls,
        rows: Sequence[Mapping[str, Any]],
        *,
        versions: Optional[Sequence[str]] = None,
        knob_paths: Optional[Sequence[str]] = None,
        layer: str = "price_factor",
    ) -> Dict[str, Any]:
        return cls.for_layer(layer).from_rows(
            rows, versions=versions, knob_paths=knob_paths
        )


__all__ = [
    "EnumerateTrades",
    "PortfolioTrades",
    "PriceTrades",
    "TradesBase",
    "TradesStep",
]
