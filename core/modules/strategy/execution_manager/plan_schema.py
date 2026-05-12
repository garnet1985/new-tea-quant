"""
工作台执行计划：显式「普通 / 强制」两套配置 + 解析。

声明形态（与 JSON 心智一致）::

    {
        "steps": ["enum", "price"],
        "execute": { "enum": {...}, "price": {...} },   # 根请求 is_force=False 时用
        "refresh": { "enum": {...}, "price": {...} },  # 根请求 is_force=True 时用
    }

``skip_cache`` 含义（同一字段、两种宿主，读法略有不同）：

- **price / capital**：``True`` → 该步 ``Flow.run(..., force_refresh=True)``（不走 Simulator
  Res **读缓存**路径，全量重算）；``False`` → ``force_refresh=False``。
- **enum**：这里的「cache」指**规划层**「下游探针已与枚举 DbCache 对齐则可省掉显式 enum」这条捷径。
  ``False`` 时在对齐条件下**可以省略**本步；``True`` 时**绝不**因对齐而省略（一定跑枚举子步骤）。
  （枚举器内部的 DbCache 仍由 ``EnumeratorRuntimeService`` / ``force_refresh`` 控制。）

根请求 ``is_force`` 只决定选用 ``execute`` 还是 ``refresh`` 表；表内再逐子步骤细调。
若要「强制 price 时枚举子步骤也带 ``force_refresh``」，在 ``refresh`` 里把 ``enum`` 的
``skip_cache`` 设为 ``True`` 即可。
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
    """单个子步骤在某一根模式（普通 / 强制）下的行为开关；见模块文档 ``skip_cache``。"""

    skip_cache: bool = False


@dataclass(frozen=True)
class WorkbenchRootPlanSpec:
    """
    用户点的根步骤（enum / price / capital）对应的完整声明。

    ``steps`` 为执行顺序；``execute`` / ``refresh`` 须为每个 ``steps`` 中的 id 各提供一条
    ``StepModeConfig``。
    """

    steps: Tuple[str, ...]
    execute: Mapping[str, StepModeConfig]
    refresh: Mapping[str, StepModeConfig]


def _mode_table(plan: WorkbenchRootPlanSpec, *, root_force: bool) -> Mapping[str, StepModeConfig]:
    return plan.refresh if root_force else plan.execute


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


# --- 显式计划表：每个根步骤一份；顺序即依赖顺序 ---

WORKBENCH_ROOT_PLANS: Dict[str, WorkbenchRootPlanSpec] = {
    "enum": WorkbenchRootPlanSpec(
        steps=("enum",),
        execute={"enum": StepModeConfig(skip_cache=False)},
        refresh={"enum": StepModeConfig(skip_cache=True)},
    ),
    "price": WorkbenchRootPlanSpec(
        steps=("enum", "price"),
        execute={
            "enum": StepModeConfig(skip_cache=False),
            "price": StepModeConfig(skip_cache=False),
        },
        refresh={
            "enum": StepModeConfig(skip_cache=False),
            "price": StepModeConfig(skip_cache=True),
        },
    ),
    "capital": WorkbenchRootPlanSpec(
        steps=("enum", "capital"),
        execute={
            "enum": StepModeConfig(skip_cache=False),
            "capital": StepModeConfig(skip_cache=False),
        },
        refresh={
            "enum": StepModeConfig(skip_cache=False),
            "capital": StepModeConfig(skip_cache=True),
        },
    ),
}


def resolve_workbench_plan(
    *,
    norm_step: str,
    is_force: bool,
    strategy_name: str,
    discovered: "DiscoveredStrategy",
) -> List[PlannedSubstep]:
    """
    解析为 ``(substep, force_refresh)``，第二元即传给各引擎的 ``force_refresh``。

    未知根步骤时退化为 ``[(norm_step, is_force)]``。
    """
    name = str(strategy_name).strip()
    root_force = bool(is_force)
    plan = WORKBENCH_ROOT_PLANS.get(norm_step)
    if plan is None:
        return [(norm_step, root_force)]

    table = _mode_table(plan, root_force=root_force)
    out: List[PlannedSubstep] = []

    for step in plan.steps:
        cfg = table.get(step)
        if cfg is None:
            raise KeyError(
                f"计划 {norm_step!r} 缺少子步骤 {step!r} 在 "
                f"{'refresh' if root_force else 'execute'} 下的配置"
            )

        if step == "enum" and norm_step in ("price", "capital"):
            if _planner_may_omit_enum(
                root_norm_step=norm_step,
                strategy_name=name,
                discovered=discovered,
            ) and not cfg.skip_cache:
                continue

        out.append((step, bool(cfg.skip_cache)))

    return out


# 兼容旧名（文档 / 外部引用）；与 ``WORKBENCH_ROOT_PLANS`` 相同。
WORKBENCH_PLAN_BY_ROOT_STEP = WORKBENCH_ROOT_PLANS

__all__ = [
    "WORKBENCH_PLAN_BY_ROOT_STEP",
    "WORKBENCH_ROOT_PLANS",
    "StepModeConfig",
    "WorkbenchRootPlanSpec",
    "resolve_workbench_plan",
]
