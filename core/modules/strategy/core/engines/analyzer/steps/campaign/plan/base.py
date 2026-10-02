"""把 attribution 配置展开成格子：overlays 逐项、matrix 笛卡尔积，或 versions 选号。

overlays 与 matrix 各自成表；overlays 自动带当前 settings 当基准格。
执行并集按 ``execute_settings`` 去重。
"""
from __future__ import annotations

from pathlib import Path
from typing import ClassVar, List, Tuple

from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.package.settings_loader import (
    load_settings_dict_from_folder,
)

from ..config import AttributionConfigBase, SettingsMatrix, SettingsOverlay
from .models import AttributionCell, ParameterPlan


class AttributionPlanBase:
    """快照 ⊕ overlay → StrategySettings；选号则只带 version_id。"""

    LAYER: ClassVar[str] = ""
    KIND: ClassVar[SimulateKind] = SimulateKind.PORTFOLIO

    @classmethod
    def expand_from_folder(
        cls,
        folder: Path,
        config: AttributionConfigBase,
    ) -> List[AttributionCell]:
        return cls.plan_from_folder(folder, config).listed_cells()

    @classmethod
    def plan_from_folder(
        cls,
        folder: Path,
        config: AttributionConfigBase,
    ) -> ParameterPlan:
        disk = load_settings_dict_from_folder(folder)
        snapshot = StrategySettings.to_usable(dict(disk))
        return cls.plan(snapshot, config)

    @classmethod
    def expand(
        cls,
        snapshot: StrategySettings,
        config: AttributionConfigBase,
    ) -> List[AttributionCell]:
        return cls.plan(snapshot, config).listed_cells()

    @classmethod
    def plan(
        cls,
        snapshot: StrategySettings,
        config: AttributionConfigBase,
    ) -> ParameterPlan:
        if config.is_select:
            selected = tuple(
                AttributionCell(
                    index=i,
                    overlay={},
                    runtime_settings={},
                    execute_settings={},
                    effective=None,
                    version_id=vid,
                    family="select",
                )
                for i, vid in enumerate(config.versions)
            )
            return ParameterPlan(selected=selected)
        overlays: Tuple[AttributionCell, ...] = ()
        if config.has_overlays:
            declared = [
                cls._from_overlay(i + 1, snapshot, row, family="overlays")
                for i, row in enumerate(config.overlays)
            ]
            overlays = (
                cls._from_snapshot(0, snapshot, family="overlays"),
                *declared,
            )
        matrix: Tuple[AttributionCell, ...] = ()
        if config.has_matrix:
            raw = config.raw_settings.get("matrix")
            rows = SettingsMatrix.expand(raw if isinstance(raw, dict) else {})
            matrix = tuple(
                cls._from_overlay(
                    i, snapshot, SettingsOverlay.from_dict(row), family="matrix"
                )
                for i, row in enumerate(rows)
            )
        return ParameterPlan(overlays=overlays, matrix=matrix)

    @classmethod
    def _from_snapshot(
        cls,
        index: int,
        snapshot: StrategySettings,
        *,
        family: str = "",
    ) -> AttributionCell:
        """当前 settings 作为 overlays 对照基准，不写进 attribution.py。"""
        return AttributionCell(
            index=index,
            overlay={},
            runtime_settings={},
            execute_settings=StrategySettings.extract_execute_settings(snapshot),
            effective=snapshot,
            version_id=None,
            family=family,
        )

    @classmethod
    def _from_overlay(
        cls,
        index: int,
        snapshot: StrategySettings,
        row: SettingsOverlay,
        *,
        family: str = "",
    ) -> AttributionCell:
        overlay = row.to_dict()
        effective = row.merge_onto(snapshot)
        return AttributionCell(
            index=index,
            overlay=overlay,
            runtime_settings=dict(overlay),
            execute_settings=StrategySettings.extract_execute_settings(effective),
            effective=effective,
            version_id=None,
            family=family,
        )
