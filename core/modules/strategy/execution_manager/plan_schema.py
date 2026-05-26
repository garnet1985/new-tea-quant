"""
工作台执行计划：显式「普通 / force_refresh」两套配置 + 解析。

声明形态（与 JSON 心智一致）::

    {
        "steps": ["enum", "price"],
        "normal": { "enum": {...}, "price": {...} },
        "force_refresh": { "enum": {...}, "price": {...} },
    }

``StepModeConfig.force_refresh``（子步骤级）：

- **price / capital**：``True`` → ``Flow.run(..., force_refresh=True)``（不走 Simulator Res 读缓存，全量重算）。
- **enum**：``True`` → 规划层绝不因指纹对齐而省掉 enum 子步骤；``False`` 时在对齐条件下可省略 enum。

根请求 ``force_refresh`` 决定选用 ``normal`` 还是 ``force_refresh`` 计划表。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, List, Mapping, Tuple

from .fingerprint_probe import enum_db_cache_aligned_with_downstream_probe
from .types import PlannedSubstep

if TYPE_CHECKING:
    from core.modules.strategy.engines.shared.data_classes.discovered_strategy import (
        DiscoveredStrategy,
    )


@dataclass(frozen=True)
class StepModeConfig:
    """单个子步骤在某种根模式（普通 / force_refresh）下的行为。"""

    force_refresh: bool = False


@dataclass(frozen=True)
class WorkbenchRootPlanSpec:
    """
    用户点的根步骤（enum / price / capital）对应的完整声明。

    ``steps`` 为执行顺序；``normal`` / ``force_refresh`` 须为每个 ``steps`` 中的 id 各提供一条配置。
    """

    steps: Tuple[str, ...]
    normal: Mapping[str, StepModeConfig]
    force_refresh: Mapping[str, StepModeConfig]


def _mode_table(
    plan: WorkbenchRootPlanSpec, *, root_force_refresh: bool
) -> Mapping[str, StepModeConfig]:
    return plan.force_refresh if root_force_refresh else plan.normal


def _planner_may_omit_enum(
    *,
    root_norm_step: str,
    strategy_name: str,
    discovered: "DiscoveredStrategy",
) -> bool:
    """为 True 时：若配置允许，可省略显式 enum。"""
    name = str(strategy_name).strip()
    if root_norm_step == "price":
        return enum_db_cache_aligned_with_downstream_probe(name, "price", discovered)
    if root_norm_step == "capital":
        return enum_db_cache_aligned_with_downstream_probe(name, "capital", discovered)
    return False


WORKBENCH_ROOT_PLANS: Dict[str, WorkbenchRootPlanSpec] = {
    "enum": WorkbenchRootPlanSpec(
        steps=("enum",),
        normal={"enum": StepModeConfig(force_refresh=False)},
        force_refresh={"enum": StepModeConfig(force_refresh=True)},
    ),
    "price": WorkbenchRootPlanSpec(
        steps=("enum", "price"),
        normal={
            "enum": StepModeConfig(force_refresh=False),
            "price": StepModeConfig(force_refresh=False),
        },
        force_refresh={
            "enum": StepModeConfig(force_refresh=False),
            "price": StepModeConfig(force_refresh=True),
        },
    ),
    "capital": WorkbenchRootPlanSpec(
        steps=("enum", "capital"),
        normal={
            "enum": StepModeConfig(force_refresh=False),
            "capital": StepModeConfig(force_refresh=False),
        },
        force_refresh={
            "enum": StepModeConfig(force_refresh=False),
            "capital": StepModeConfig(force_refresh=True),
        },
    ),
}


def resolve_workbench_plan(
    *,
    norm_step: str,
    force_refresh: bool,
    strategy_name: str,
    discovered: "DiscoveredStrategy",
) -> List[PlannedSubstep]:
    """
    解析为 ``(substep, force_refresh)``，第二元传给各引擎的 ``force_refresh``。

    未知根步骤时退化为 ``[(norm_step, force_refresh)]``。
    """
    name = str(strategy_name).strip()
    root_force_refresh = bool(force_refresh)
    plan = WORKBENCH_ROOT_PLANS.get(norm_step)
    if plan is None:
        return [(norm_step, root_force_refresh)]

    table = _mode_table(plan, root_force_refresh=root_force_refresh)
    out: List[PlannedSubstep] = []

    for step in plan.steps:
        cfg = table.get(step)
        if cfg is None:
            raise KeyError(
                f"计划 {norm_step!r} 缺少子步骤 {step!r} 在 "
                f"{'force_refresh' if root_force_refresh else 'normal'} 下的配置"
            )

        if step == "enum" and norm_step in ("price", "capital"):
            if _planner_may_omit_enum(
                root_norm_step=norm_step,
                strategy_name=name,
                discovered=discovered,
            ) and not cfg.force_refresh:
                continue

        out.append((step, bool(cfg.force_refresh)))

    return out


__all__ = [
    "WORKBENCH_ROOT_PLANS",
    "StepModeConfig",
    "WorkbenchRootPlanSpec",
    "resolve_workbench_plan",
]
