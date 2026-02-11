"""
通用任务执行器模块

本模块提供了两种任务执行器：
- ProcessWorker: 基于多进程的CPU密集型任务执行器
- MultiThreadWorker: 基于多线程的IO密集型任务执行器（原 FuturesWorker）

新的模块化架构（推荐使用）：
- executors: 执行器（MultiThreadExecutor, ProcessExecutor）
- queues: 任务源（ListJobSource）
- monitors: 监控器（MemoryMonitor）
- schedulers: 调度器（MemoryAwareScheduler）
- aggregators: 聚合器（SimpleAggregator）
- error_handlers: 错误处理器（SimpleErrorHandler）
- orchestrator: 编排器（Orchestrator）
"""

# ============================================================================
# 向后兼容：保留旧的导入
# ============================================================================

# 导入多进程执行器
from .multi_process.process_worker import (
    ProcessWorker,
    ExecutionMode as ProcessExecutionMode,
    JobStatus as ProcessJobStatus,
    JobResult as ProcessJobResult
)

# 导入多线程执行器
from .multi_thread.futures_worker import (
    MultiThreadWorker,
    ExecutionMode as ThreadExecutionMode,
    JobStatus as ThreadJobStatus,
    JobResult as ThreadJobResult,
)

# Memory-aware 批量调度器（旧版本，保留向后兼容）
from .memory_aware_scheduler import MemoryAwareBatchScheduler

# ============================================================================
# 新的模块化架构（推荐使用）
# ============================================================================

# Executors
from .executors import (
    Executor,
    JobResult,
    JobStatus,
    MultiThreadExecutor,
    ProcessExecutor,
)

# Queues
from .queues import (
    JobSource,
    ListJobSource,
)

# Monitors
from .monitors import (
    Monitor,
    MemoryMonitor,
)

# Schedulers
from .schedulers import (
    Scheduler,
    MemoryAwareScheduler,
)

# Aggregators
from .aggregators import (
    Aggregator,
    SimpleAggregator,
)

# Error Handlers
from .error_handlers import (
    ErrorHandler,
    ErrorAction,
    SimpleErrorHandler,
)

# Orchestrator
from .orchestrator import Orchestrator

__all__ = [
    # 向后兼容的导入
    'ProcessWorker',
    'ProcessExecutionMode',
    'ProcessJobStatus',
    'ProcessJobResult',
    'MultiThreadWorker',
    'ThreadExecutionMode',
    'ThreadJobStatus',
    'ThreadJobResult',
    'MemoryAwareBatchScheduler',  # 旧版本
    
    # 新的模块化架构
    # Executors
    'Executor',
    'JobResult',
    'JobStatus',
    'MultiThreadExecutor',
    'ProcessExecutor',
    # Queues
    'JobSource',
    'ListJobSource',
    # Monitors
    'Monitor',
    'MemoryMonitor',
    # Schedulers
    'Scheduler',
    'MemoryAwareScheduler',
    # Aggregators
    'Aggregator',
    'SimpleAggregator',
    # Error Handlers
    'ErrorHandler',
    'ErrorAction',
    'SimpleErrorHandler',
    # Orchestrator
    'Orchestrator',
]

# 版本信息（与项目版本保持一致）
__version__ = "0.1.0"
__author__ = "New Tea Quant Team"
__description__ = "通用任务执行器模块 - 支持多进程和多线程执行，模块化架构"
