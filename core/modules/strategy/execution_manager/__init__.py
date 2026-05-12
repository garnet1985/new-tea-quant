"""策略工作台步骤执行管理（规划 + 同步执行 + 宿主适配）。

与 ``engines`` 并列；规划与同步执行见 ``planning`` / ``execution``，宿主适配见 ``adapters``。
"""

from .adapters import run_workbench_step_via_cli_contract, submit_workbench_step_via_bff_contract
from .execution import execute_workbench_plan_sync, run_workbench_substep_for_snapshot
from .planning import plan_workbench_substeps
from .workbench_disk_progress import get_step_progress
from .workbench_resolve import normalize_step, resolve_discovered_strategy
from .plan_schema import (
    WORKBENCH_PLAN_BY_ROOT_STEP,
    WORKBENCH_ROOT_PLANS,
    StepModeConfig,
    WorkbenchRootPlanSpec,
    resolve_workbench_plan,
)
from .types import (
    PlannedSubstep,
    ProgressCallback,
    ProgressSink,
    WorkbenchExecutionResult,
    WorkbenchSubstep,
)

__all__ = [
    "WORKBENCH_PLAN_BY_ROOT_STEP",
    "WORKBENCH_ROOT_PLANS",
    "StepModeConfig",
    "WorkbenchRootPlanSpec",
    "PlannedSubstep",
    "ProgressCallback",
    "ProgressSink",
    "WorkbenchExecutionResult",
    "WorkbenchSubstep",
    "execute_workbench_plan_sync",
    "get_step_progress",
    "normalize_step",
    "plan_workbench_substeps",
    "resolve_discovered_strategy",
    "resolve_workbench_plan",
    "run_workbench_substep_for_snapshot",
    "run_workbench_step_via_cli_contract",
    "submit_workbench_step_via_bff_contract",
]
