"""
Backtest Engine - Shared基础组件

提供真正共用的基础组件：
- types.py：基础类型定义（Job、JobContext、JobReport等）
- context.py：执行上下文（ExecutionContext）
- base_planner.py：规划器基类（BasePlanner）

设计原则：
- shared只包含真正共用的基础组件
- entity_based和slice_based各自有自己的调度逻辑
- MachineInfo 见 core.infra.machine_capacity
"""

__version__ = "0.1.0"

# 暴露共用的基础API
from .types import (
    JobFailurePhase,
    ExecutionBackend,
    ExecuteMode,
    Job,
    JobContext,
    JobReport,
    RunProgress,
    JobFailure,
    DispatchResult,
)

from .context import ExecutionContext

from .base_planner import BasePlanner


__all__ = [
    # Types
    "JobFailurePhase",
    "ExecutionBackend",
    "ExecuteMode",
    "Job",
    "JobContext",
    "JobReport",
    "RunProgress",
    "JobFailure",
    "DispatchResult",
    # Context
    "ExecutionContext",
    # BasePlanner
    "BasePlanner",
]
