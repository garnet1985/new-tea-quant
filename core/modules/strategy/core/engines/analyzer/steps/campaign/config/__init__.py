"""战役配置步：读 attribution.py → 标准化配置。

pipeline 只调 ``AttributionConfig.load(..., layer=)``；层差异在子类。
"""
from __future__ import annotations

from typing import Any, Type

from core.modules.strategy.core.enums import SimulateKind

from ..layers import declare_layer, pick_layer
from .base import AttributionConfigBase
from .inputs import MAX_CELLS, expand_axes, parse_axes
from .loader import ATTRIBUTION_FILE_NAME
from .overlay import SettingsOverlay

EnumerateAttributionConfig = declare_layer(
    "EnumerateAttributionConfig",
    AttributionConfigBase,
    "enumerate",
    SimulateKind.ENUMERATE,
)
PriceAttributionConfig = declare_layer(
    "PriceAttributionConfig",
    AttributionConfigBase,
    "price_factor",
    SimulateKind.PRICE_FACTOR,
)
PortfolioAttributionConfig = declare_layer(
    "PortfolioAttributionConfig",
    AttributionConfigBase,
    "portfolio",
    SimulateKind.PORTFOLIO,
)

_BY_LAYER: dict[str, Type[AttributionConfigBase]] = {
    "enumerate": EnumerateAttributionConfig,
    "price_factor": PriceAttributionConfig,
    "portfolio": PortfolioAttributionConfig,
}


class AttributionConfig:
    """配置步门面：按层分发到对应配置类。"""

    @classmethod
    def for_layer(cls, layer: Any) -> Type[AttributionConfigBase]:
        """按层返回配置类。"""
        return pick_layer(_BY_LAYER, layer, PortfolioAttributionConfig)

    @classmethod
    def load(cls, strategy_folder, *, layer: str = "", strategy_key=None):
        """从策略目录读取该层配置。"""
        return cls.for_layer(layer).load(
            strategy_folder, strategy_key=strategy_key
        )

    @classmethod
    def to_usable(cls, settings, *, layer: str = ""):
        """校验并返回该层可用配置。"""
        return cls.for_layer(layer).to_usable(settings)


__all__ = [
    "ATTRIBUTION_FILE_NAME",
    "MAX_CELLS",
    "AttributionConfig",
    "AttributionConfigBase",
    "EnumerateAttributionConfig",
    "PriceAttributionConfig",
    "PortfolioAttributionConfig",
    "SettingsOverlay",
    "expand_axes",
    "parse_axes",
]
