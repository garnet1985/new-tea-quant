"""战役单笔步：价格层机会铺平 → XGB / SHAP。

pipeline 只在 spa 调用 ``TradesStep.run``；其他层返回 skipped。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Type

from core.modules.strategy.core.enums import SimulateKind

from ..layers import declare_layer, pick_layer
from ..plan import AttributionCell
from .base import TradesBase

EnumerateTrades = declare_layer(
    "EnumerateTrades", TradesBase, "enumerate", SimulateKind.ENUMERATE
)
PriceTrades = declare_layer(
    "PriceTrades", TradesBase, "price_factor", SimulateKind.PRICE_FACTOR
)
PortfolioTrades = declare_layer(
    "PortfolioTrades", TradesBase, "portfolio", SimulateKind.PORTFOLIO
)

_BY_LAYER: dict[str, Type[TradesBase]] = {
    "enumerate": EnumerateTrades,
    "price_factor": PriceTrades,
    "portfolio": PortfolioTrades,
}


class TradesStep:
    """单笔步门面：按层分发（仅 spa 有实质工作）。"""

    @classmethod
    def for_layer(cls, layer: Any) -> Type[TradesBase]:
        """按层返回单笔步骤类。"""
        return pick_layer(_BY_LAYER, layer, PriceTrades)

    @classmethod
    def run(
        cls,
        folder: Path,
        unique_cells: Sequence[AttributionCell],
        executed: Mapping[str, Any],
        *,
        layer: str = "price_factor",
    ) -> Dict[str, Any]:
        """铺平该层机会并做单笔模型。"""
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
        """用已有行做单笔模型。"""
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
