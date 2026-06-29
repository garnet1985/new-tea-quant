"""
Backtest Scheduler - Shared基础组件

提供真正共用的基础组件：
- job_pipeline.py：General JobPipeline框架（ProcessPoolExecutor/ThreadPoolExecutor）
- types.py：基础类型定义（Job、JobContext、JobReport等）
- executor.py：执行器实现
- utils.py：基础工具函数（resolve_memory_budget_mb等）

设计原则：
- shared只包含真正共用的基础组件
- timeline_based和slice_based各自有自己的调度逻辑
- 不混合两种不同的调度方式
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

from .job_pipeline import (
    JobPipeline,
    JobPipelineSettings,
    JobExecutor,
    create_job_executor,
    OnResultHook,
    OnReleaseHook,
    ExecuteFn,
)

# 共用的基础工具函数（不包含完整的调度逻辑）
from .utils import (
    resolve_memory_budget_mb,
    resolve_memory_floor_mb,
)


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
    # JobPipeline
    "JobPipeline",
    "JobPipelineSettings",
    "JobExecutor",
    "create_job_executor",
    "OnResultHook",
    "OnReleaseHook",
    "ExecuteFn",
    # Utils
    "resolve_memory_budget_mb",
    "resolve_memory_floor_mb",
]