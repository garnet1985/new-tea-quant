"""工作台步骤执行管理 — 规划入口（委托 ``plan_schema`` 显式声明解析）。"""

from __future__ import annotations

from typing import TYPE_CHECKING, List

from .plan_schema import resolve_workbench_plan
from .types import PlannedSubstep

if TYPE_CHECKING:
    from core.modules.strategy.engines.shared.data_classes.discovered_strategy import (
        DiscoveredStrategy,
    )

__all__ = [
    "plan_workbench_substeps",
]


def plan_workbench_substeps(
    *,
    norm_step: str,
    is_force: bool,
    strategy_name: str,
    discovered: "DiscoveredStrategy",
) -> List[PlannedSubstep]:
    """见 ``plan_schema.resolve_workbench_plan`` 与 ``WORKBENCH_PLAN_BY_ROOT_STEP``。"""
    return resolve_workbench_plan(
        norm_step=norm_step,
        is_force=is_force,
        strategy_name=strategy_name,
        discovered=discovered,
    )
