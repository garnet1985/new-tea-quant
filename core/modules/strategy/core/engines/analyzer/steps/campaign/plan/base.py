"""把 attribution 按层 inputs 展开成格子：默认 oaat，cross 为笛卡尔积。

自动带当前 settings 当基准格。执行并集按 ``execute_settings`` 去重。
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import ClassVar, List

from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.package.settings_loader import (
    load_settings_dict_from_folder,
)

from ..config import AttributionConfigBase, SettingsOverlay
from ..config.inputs import (
    MAX_CELLS,
    cell_count,
    cost_gate_message,
    expand_axes,
    merge_user_and_defaults,
    parse_axes,
)
from .models import AttributionCell, ParameterPlan

_LOG = logging.getLogger(__name__)


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

        layer = str(config.LAYER or cls.LAYER or "").strip()
        family = "cross" if config.cross else "inputs"
        snap_raw = dict(snapshot.raw_settings)
        merged = merge_user_and_defaults(layer, config.layer_inputs, snap_raw)
        axes = parse_axes(layer, merged, snapshot=snap_raw)
        nominal = cell_count(axes, cross=config.cross)
        if nominal > MAX_CELLS:
            raise ValueError(
                f"展开约 {nominal} 格超过上限 {MAX_CELLS}；"
                "请减少 values 或关闭 cross"
            )
        warning = cost_gate_message(
            nominal, snap_raw, cross=config.cross
        )
        if warning and not warning.startswith("WARNING:"):
            raise ValueError(warning)
        if warning:
            _LOG.warning("%s", warning)

        rows = expand_axes(axes, cross=config.cross)
        declared = [
            cls._from_overlay(
                i + 1, snapshot, SettingsOverlay.from_dict(row), family=family
            )
            for i, row in enumerate(rows)
        ]
        cells = cls._dedupe_execute(
            (cls._from_snapshot(0, snapshot, family=family), *declared)
        )
        return ParameterPlan(cells=cells, cost_warning=warning or "")

    @classmethod
    def _dedupe_execute(
        cls, cells: tuple[AttributionCell, ...]
    ) -> tuple[AttributionCell, ...]:
        """按 execute_settings 去重，保留先出现的格（通常是基准）。"""
        seen: set[str] = set()
        kept: List[AttributionCell] = []
        for cell in cells:
            key = repr(cell.execute_settings)
            if key in seen:
                continue
            seen.add(key)
            kept.append(cell)
        return tuple(
            AttributionCell(
                index=i,
                overlay=cell.overlay,
                runtime_settings=cell.runtime_settings,
                execute_settings=cell.execute_settings,
                effective=cell.effective,
                version_id=cell.version_id,
                family=cell.family,
            )
            for i, cell in enumerate(kept)
        )

    @classmethod
    def _from_snapshot(
        cls,
        index: int,
        snapshot: StrategySettings,
        *,
        family: str = "",
    ) -> AttributionCell:
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
