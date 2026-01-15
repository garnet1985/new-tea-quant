#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
简单列表任务源
"""

from typing import Any, List

from .base import JobSource


class ListJobSource(JobSource):
    """
    简单列表任务源
    
    从预加载的列表中提供任务
    """
    
    def __init__(self, jobs: List[Any]):
        """
        初始化
        
        Args:
            jobs: 任务列表
        """
        self._jobs = list(jobs)
        self._cursor = 0
    
    def get_batch(self, size: int) -> List[Any]:
        """获取一批任务"""
        if not self.has_more():
            return []
        
        end = min(self._cursor + size, len(self._jobs))
        batch = self._jobs[self._cursor:end]
        self._cursor = end
        return batch
    
    def has_more(self) -> bool:
        """是否还有更多任务"""
        return self._cursor < len(self._jobs)
    
    def total_count(self) -> int:
        """获取任务总数"""
        return len(self._jobs)
    
    def reset(self) -> None:
        """重置任务源"""
        self._cursor = 0
