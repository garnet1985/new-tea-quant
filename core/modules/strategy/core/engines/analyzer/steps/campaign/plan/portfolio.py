"""组合层计划：只展开资金分配，锚定当前 settings。

不跟枚举 / 价格共用副本身份。每一格只改一个分配轴。
"""
from __future__ import annotations

from typing import Any, List

from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.enums import SimulateKind

from ..config import AttributionConfigBase, SettingsOverlay
from ..config.inputs import MAX_CELLS, assign_path, value_at
from .base import AttributionPlanBase
from .models import AttributionCell, ParameterPlan


class PortfolioAttributionPlan(AttributionPlanBase):
    LAYER = "portfolio"
    KIND = SimulateKind.PORTFOLIO

    @classmethod
    def plan(
        cls,
        snapshot: StrategySettings,
        config: AttributionConfigBase,
    ) -> ParameterPlan:
        snap = dict(snapshot.raw_settings)
        axes = config.allocation_axes(snap)
        if not axes:
            raise ValueError(
                "组合层归因没有可扫的资金分配轴；"
                "请在 attribution.allocation 里写 values，或去掉空的 allocation"
            )
        pending = 0
        for path, values in axes.items():
            current = value_at(snap, path)
            pending += sum(1 for item in values if not _same(item, current))
        if pending + 1 > MAX_CELLS:
            raise ValueError(
                f"资金分配展开约 {pending + 1} 格超过上限 {MAX_CELLS}"
            )
        cells: List[AttributionCell] = [
            cls._from_snapshot(0, snapshot, family="allocation")
        ]
        index = 1
        for path, values in axes.items():
            current = value_at(snap, path)
            for item in values:
                if _same(item, current):
                    continue
                overlay: dict = {}
                assign_path(overlay, path, item)
                cells.append(
                    cls._from_overlay(
                        index,
                        snapshot,
                        SettingsOverlay.from_dict(overlay),
                        family="allocation",
                    )
                )
                index += 1
        return ParameterPlan(cells=cls._dedupe_execute(tuple(cells)))


def _same(left: Any, right: Any) -> bool:
    if left == right:
        return True
    if (
        isinstance(left, bool)
        or isinstance(right, bool)
        or not isinstance(left, (int, float))
        or not isinstance(right, (int, float))
    ):
        return False
    return abs(float(left) - float(right)) < 1e-9
