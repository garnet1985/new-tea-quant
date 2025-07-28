"""
通用任务执行器模块
"""

from .worker import (
    JobWorker,
    JobResult,
    JobStatus,
    ExecutionMode
)

__all__ = [
    'JobWorker',
    'JobResult', 
    'JobStatus',
    'ExecutionMode'
] 