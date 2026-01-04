"""
通用任务执行器模块

本模块提供了两种任务执行器：
- ProcessWorker: 基于多进程的CPU密集型任务执行器
- FuturesWorker: 基于多线程的IO密集型任务执行器

目录结构：
- multi_process/: 多进程执行器相关文件
- multi_thread/: 多线程执行器相关文件
"""

# 导入多进程执行器
from .multi_process.process_worker import (
    ProcessWorker,
    ExecutionMode as ProcessExecutionMode,
    JobStatus as ProcessJobStatus,
    JobResult as ProcessJobResult
)

# 导入多线程执行器
from .multi_thread.futures_worker import (
    FuturesWorker,
    ExecutionMode as ThreadExecutionMode,
    JobStatus as ThreadJobStatus,
    JobResult as ThreadJobResult
)

# 为了向后兼容，保留原有的导入方式
from .multi_thread.futures_worker import (
    ExecutionMode as ThreadExecutionMode,
    JobStatus,
    JobResult
)

__all__ = [
    # 多进程执行器
    'ProcessWorker',
    'ProcessExecutionMode',
    'ProcessJobStatus', 
    'ProcessJobResult',
    
    # 多线程执行器
    'FuturesWorker',
    'ThreadExecutionMode',
    'ThreadJobStatus',
    'ThreadJobResult',
    
    # 向后兼容的导入
    'ExecutionMode',
    'JobStatus',
    'JobResult'
]

# 版本信息
__version__ = "2.0.0"
__author__ = "Stocks-Py Team"
__description__ = "通用任务执行器模块 - 支持多进程和多线程执行"