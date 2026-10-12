"""归因入口。按层跑战役。"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Union

from core.modules.strategy.core.enums import SimulateKind

from .pipeline import AttributionPipeline
from .steps.campaign.report import CampaignPresenter


class Analyzer:
    """按层归因的入口。"""

    Campaign = AttributionPipeline
    CampaignPresenter = CampaignPresenter

    @classmethod
    def attribute(
        cls,
        key_or_id: Union[str, Path],
        *,
        kind: Union[SimulateKind, str],
        ignore_cache: bool = False,
    ) -> Dict[str, Any]:
        """读 attribution.py，按层对照旋钮，写出战役总结。"""
        return AttributionPipeline.run(
            key_or_id, kind=kind, ignore_cache=ignore_cache
        )

    @classmethod
    def attribute_enumerate(
        cls,
        key_or_id: Union[str, Path],
        *,
        ignore_cache: bool = False,
    ) -> Dict[str, Any]:
        """跑枚举层归因。"""
        return cls.attribute(
            key_or_id, kind=SimulateKind.ENUMERATE, ignore_cache=ignore_cache
        )

    @classmethod
    def attribute_price(
        cls,
        key_or_id: Union[str, Path],
        *,
        ignore_cache: bool = False,
    ) -> Dict[str, Any]:
        """跑价格层归因。"""
        return cls.attribute(
            key_or_id, kind=SimulateKind.PRICE_FACTOR, ignore_cache=ignore_cache
        )

    @classmethod
    def attribute_portfolio(
        cls,
        key_or_id: Union[str, Path],
        *,
        ignore_cache: bool = False,
    ) -> Dict[str, Any]:
        """跑组合层归因。"""
        return cls.attribute(
            key_or_id, kind=SimulateKind.PORTFOLIO, ignore_cache=ignore_cache
        )
