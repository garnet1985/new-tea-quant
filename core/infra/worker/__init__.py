"""
Worker模块 - 提供Dispatch规划和任务类型定义

核心功能：
- Dispatch规划：基于内存/时间约束优化并发执行
- 类型定义：JobResult、JobStatus、DispatchPlan等

已废弃功能：
- ProcessWorker：已迁移到job_pipeline模块
- MultiThreadWorker：不推荐使用
"""

# ============================================================================
# Facade入口（推荐使用）
# ============================================================================

from .worker import Worker

# ============================================================================
# 向后兼容导出（不推荐直接使用）
# ============================================================================

# 类型定义
from .multi_process.process_worker import JobResult, JobStatus
from .dispatch_planner import DispatchPlan, resolve_dispatch_plan
from .dispatch_time_planner import TimeDispatchPlan, resolve_time_dispatch_plan
from .dispatch_probe import should_run_dispatch_probe

__all__ = [
    # Facade入口（推荐使用）
    'Worker',

    # 类型定义（向后兼容）
    'DispatchPlan',
    'TimeDispatchPlan',
    'JobResult',
    'JobStatus',

    # API方法（向后兼容）
    'resolve_dispatch_plan',
    'resolve_time_dispatch_plan',
    'should_run_dispatch_probe',
]

# 版本信息（与 core.system 保持一致）
from core.system import get_version

__version__ = get_version()
__author__ = "New Tea Quant Team"
__description__ = "Worker模块 - 提供Dispatch规划和任务类型定义"
