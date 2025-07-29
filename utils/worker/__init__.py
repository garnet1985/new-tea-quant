"""
通用任务执行器模块
"""

from .futures_worker import (
    FuturesWorker
)

__all__ = [
    'JobWorker',
    'FuturesWorker',  # 新增
    'JobResult', 
    'JobStatus',
    'ExecutionMode'
] 