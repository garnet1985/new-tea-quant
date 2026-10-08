"""归因入口。按层跑战役，或做滚动验证。"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Union

from core.modules.strategy.core.enums import SimulateKind

from .pipeline import AttributionPipeline, RollingPipeline
from .steps.campaign.report import CampaignPresenter
from .steps.rolling.present import RollingPresenter


class Analyzer:
    """按层归因和滚动验证的入口。"""

    Campaign = AttributionPipeline
    Rolling = RollingPipeline
    CampaignPresenter = CampaignPresenter
    RollingPresenter = RollingPresenter

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

    @classmethod
    # TODO: 滚动验证的产品口径还没定，整段先留着，不要当已完成功能。
    def rolling(
        cls,
        key_or_id: Union[str, Path],
        *,
        ignore_cache: bool = False,
    ) -> Dict[str, Any]:
        """读 attribution.py 的 rolling 窗口，写出滚动总结。"""
        return RollingPipeline.run(key_or_id, ignore_cache=ignore_cache)
