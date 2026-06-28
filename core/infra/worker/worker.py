#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Worker模块Facade入口

提供Dispatch规划和任务类型定义的高层API。
"""

from __future__ import annotations

# 类型定义（高频使用）
from .multi_process.process_worker import JobResult, JobStatus
from .dispatch_planner import DispatchPlan, resolve_dispatch_plan, resolve_memory_budget_mb
from .dispatch_time_planner import TimeDispatchPlan, resolve_time_dispatch_plan
from .dispatch_probe import should_run_dispatch_probe


class Worker:
    """
    Worker模块Facade类

    提供Dispatch规划和任务类型定义的高层API。
    """

    # 类型定义（高频使用）
    DispatchPlan = DispatchPlan
    TimeDispatchPlan = TimeDispatchPlan
    JobResult = JobResult
    JobStatus = JobStatus

    # 高层API（高频使用）
    @staticmethod
    def resolve_dispatch_plan(*args, **kwargs):
        """解析dispatch规划（基于内存）"""
        return resolve_dispatch_plan(*args, **kwargs)

    @staticmethod
    def resolve_time_dispatch_plan(*args, **kwargs):
        """解析time dispatch规划（基于时间）"""
        return resolve_time_dispatch_plan(*args, **kwargs)

    @staticmethod
    def resolve_memory_budget_mb(*args, **kwargs):
        """解析内存预算"""
        return resolve_memory_budget_mb(*args, **kwargs)

    @staticmethod
    def should_run_dispatch_probe(*args, **kwargs):
        """判断是否运行dispatch probe"""
        return should_run_dispatch_probe(*args, **kwargs)


__all__ = ['Worker']