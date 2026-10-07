"""把共用 inputs 展开成格子。默认一次只改一个轴。"""
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
    collect_joint_sweep,
    cost_gate_message,
    expand_axes,
    expand_joint_groups,
    joint_cell_count,
    merge_user_and_defaults,
    parse_axes,
)
from .models import AttributionCell, ParameterPlan

_LOG = logging.getLogger(__name__)


def _is_price_replay_axis(path: str) -> bool:
    """``simulation.price`` 只改变价格回放的合并方式，不产生新的枚举。"""
    text = str(path or "").strip()
    return text == "simulation.price" or text.startswith("simulation.price.")


class AttributionPlanBase:
    """快照 ⊕ overlay → StrategySettings；选号则只带 version_id。"""

    LAYER: ClassVar[str] = ""
    KIND: ClassVar[SimulateKind] = SimulateKind.PORTFOLIO

    @classmethod
    def _skip_price_replay_axes(cls) -> bool:
        """枚举战役不展开价格回放轴。"""
        return False

    @classmethod
    def expand_from_folder(
        cls,
        folder: Path,
        config: AttributionConfigBase,
    ) -> List[AttributionCell]:
        """读策略目录里的当前设置并返回格子。"""
        return cls.plan_from_folder(folder, config).listed_cells()

    @classmethod
    def plan_from_folder(
        cls,
        folder: Path,
        config: AttributionConfigBase,
    ) -> ParameterPlan:
        """读策略目录里的当前设置并展开成计划。"""
        disk = load_settings_dict_from_folder(folder)
        snapshot = StrategySettings.to_usable(dict(disk))
        return cls.plan(snapshot, config)

    @classmethod
    def expand(
        cls,
        snapshot: StrategySettings,
        config: AttributionConfigBase,
    ) -> List[AttributionCell]:
        """把当前设置展开成格子。"""
        return cls.plan(snapshot, config).listed_cells()

    @classmethod
    def plan(
        cls,
        snapshot: StrategySettings,
        config: AttributionConfigBase,
    ) -> ParameterPlan:
        """把当前设置展开成计划。"""
        # TODO: 全轴 cross 能展开，但报告仍按单因素讲，产品还没完成。
        cross = bool(config.cross)
        family = "cross" if cross else "oaat"
        snap_raw = dict(snapshot.raw_settings)
        # 共用展格：只读顶层 inputs；与 CLI 层无关
        merged = merge_user_and_defaults(
            "campaign", config.campaign_inputs, snap_raw
        )
        joint_groups = () if cross else tuple(collect_joint_sweep(config.raw_settings))
        if cls._skip_price_replay_axes():
            merged = {
                path: spec
                for path, spec in merged.items()
                if not _is_price_replay_axis(path)
            }
            kept_groups = []
            for group in joint_groups:
                kept = tuple(
                    path for path in group if not _is_price_replay_axis(path)
                )
                if len(kept) >= 2:
                    kept_groups.append(kept)
            joint_groups = tuple(kept_groups)
        axes = parse_axes("campaign", merged, snapshot=snap_raw)
        nominal = cell_count(axes, cross=cross)
        if joint_groups:
            nominal += joint_cell_count(axes, joint_groups)
        if nominal > MAX_CELLS:
            raise ValueError(
                f"展开约 {nominal} 格超过上限 {MAX_CELLS}；"
                "请减少 values、缩小 joint_sweep 或关闭 cross"
            )
        warning = cost_gate_message(nominal, snap_raw, cross=cross)
        if warning and not warning.startswith("WARNING:"):
            raise ValueError(warning)
        if warning:
            _LOG.warning("%s", warning)

        rows = expand_axes(axes, cross=cross)
        declared = [
            cls._from_overlay(
                i + 1, snapshot, SettingsOverlay.from_dict(row), family=family
            )
            for i, row in enumerate(rows)
        ]
        joint_declared: List[AttributionCell] = []
        if joint_groups:
            joint_rows = expand_joint_groups(axes, joint_groups)
            base_index = len(declared) + 1
            joint_declared = [
                cls._from_overlay(
                    base_index + i,
                    snapshot,
                    SettingsOverlay.from_dict(row),
                    family="joint",
                )
                for i, row in enumerate(joint_rows)
            ]
        cells = cls._dedupe_execute(
            (
                cls._from_snapshot(0, snapshot, family=family),
                *declared,
                *joint_declared,
            )
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
