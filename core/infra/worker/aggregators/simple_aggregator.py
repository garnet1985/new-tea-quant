#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
简单聚合器
"""

from typing import Any, Dict

from .base import Aggregator
from ..executors.base import JobResult, JobStatus


class SimpleAggregator(Aggregator):
    """
    简单聚合器
    
    统计基本的执行指标：
    - 成功/失败数量
    - 总耗时
    - 平均耗时
    """
    
    def __init__(self):
        """初始化"""
        self._results: list[JobResult] = []
        self._total_duration = 0.0
        self._success_count = 0
        self._failed_count = 0
    
    def add_result(self, result: JobResult) -> None:
        """添加一个执行结果"""
        self._results.append(result)
        self._total_duration += result.duration
        
        if result.status == JobStatus.COMPLETED:
            self._success_count += 1
        elif result.status == JobStatus.FAILED:
            self._failed_count += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """获取聚合后的全局视图"""
        total = len(self._results)
        avg_duration = self._total_duration / total if total > 0 else 0.0
        
        return {
            'total_jobs': total,
            'success_count': self._success_count,
            'failed_count': self._failed_count,
            'total_duration': self._total_duration,
            'avg_duration': avg_duration,
            'success_rate': (self._success_count / total * 100.0) if total > 0 else 0.0,
        }
    
    def reset(self) -> None:
        """重置聚合器状态"""
        self._results.clear()
        self._total_duration = 0.0
        self._success_count = 0
        self._failed_count = 0
