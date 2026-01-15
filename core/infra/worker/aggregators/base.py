#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Aggregator 基类/接口定义
"""

from abc import ABC, abstractmethod
from typing import Any, Dict

from ..executors.base import JobResult


class Aggregator(ABC):
    """
    聚合器基类
    
    职责：将单个 JobResult 聚合成「全局视图」
    - 业务层统计（如 total_opportunity_count）
    - 性能统计（如 avg_time_per_job_ms, total_db_time 等）
    - 可选：增量 flush 到磁盘
    """
    
    @abstractmethod
    def add_result(self, result: JobResult) -> None:
        """
        添加一个执行结果
        
        Args:
            result: 任务执行结果
        """
        pass
    
    @abstractmethod
    def get_summary(self) -> Dict[str, Any]:
        """
        获取聚合后的全局视图
        
        Returns:
            汇总统计字典
        """
        pass
    
    def reset(self) -> None:
        """
        重置聚合器状态（可选实现）
        """
        pass
    
    def flush(self) -> None:
        """
        将聚合结果刷新到磁盘（可选实现）
        """
        pass
