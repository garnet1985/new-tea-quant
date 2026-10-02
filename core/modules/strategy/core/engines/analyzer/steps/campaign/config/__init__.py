"""战役配置步：读 attribution.py → 标准化配置。

pipeline 只调 ``AttributionConfig.load(..., layer=)``；层差异在子类。
"""
from __future__ import annotations

from typing import Any, Type

from .base import AttributionConfigBase
from .enumerate import EnumerateAttributionConfig
from .grid import SettingsMatrix
from .loader import ATTRIBUTION_FILE_NAME
from .overlay import SettingsOverlay
from .portfolio import PortfolioAttributionConfig
from .price import PriceAttributionConfig

_BY_LAYER: dict[str, Type[AttributionConfigBase]] = {
    EnumerateAttributionConfig.LAYER: EnumerateAttributionConfig,
    PriceAttributionConfig.LAYER: PriceAttributionConfig,
    PortfolioAttributionConfig.LAYER: PortfolioAttributionConfig,
}


class AttributionConfig:
    """配置步门面：按层分发到对应配置类。"""

    @classmethod
    def for_layer(cls, layer: Any) -> Type[AttributionConfigBase]:
        focus = str(getattr(layer, "value", layer) or "").strip()
        step = _BY_LAYER.get(focus)
        if step is None:
            return PortfolioAttributionConfig
        return step

    @classmethod
    def load(cls, strategy_folder, *, layer: str = "", strategy_key=None):
        return cls.for_layer(layer).load(
            strategy_folder, strategy_key=strategy_key
        )

    @classmethod
    def to_usable(cls, settings, *, layer: str = ""):
        return cls.for_layer(layer).to_usable(settings)


# 旧名已删；对外只用 AttributionConfig / 各层子类。
__all__ = [
    "ATTRIBUTION_FILE_NAME",
    "AttributionConfig",
    "AttributionConfigBase",
    "EnumerateAttributionConfig",
    "PriceAttributionConfig",
    "PortfolioAttributionConfig",
    "SettingsMatrix",
    "SettingsOverlay",
]
