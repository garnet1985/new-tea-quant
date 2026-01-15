"""
执行器模块

提供多种并发执行策略：
- MultiThreadExecutor: 基于多线程的执行器（原 FuturesExecutor）
- ProcessExecutor: 基于多进程的执行器
"""

from .base import Executor, JobResult, JobStatus
from .futures_executor import MultiThreadExecutor
from .process_executor import ProcessExecutor

__all__ = [
    'Executor',
    'JobResult',
    'JobStatus',
    # 多线程执行器
    'MultiThreadExecutor',
    'ProcessExecutor',
]
