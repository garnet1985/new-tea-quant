"""
队列/任务源模块

提供多种任务源实现：
- ListJobSource: 简单列表任务源
"""

from .base import JobSource
from .list_source import ListJobSource

__all__ = [
    'JobSource',
    'ListJobSource',
]
