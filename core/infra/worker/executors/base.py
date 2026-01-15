#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Executor 基类/接口定义
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class JobStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class JobResult:
    """任务执行结果"""
    job_id: str
    status: JobStatus
    result: Any = None
    error: Exception = None
    duration: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def __str__(self):
        return f"JobResult(job_id={self.job_id}, status={self.status.value}, duration={self.duration:.2f}s)"


class Executor(ABC):
    """
    执行器基类
    
    职责：负责"如何并发执行一批 jobs"
    - 输入：`jobs: List[Dict[str, Any]]`，每个 job 格式为 `{'id': ..., 'data': ...}`
    - 输出：`List[JobResult]`
    - 不关心调度、监控、聚合等，只负责执行
    """
    
    @abstractmethod
    def run_jobs(self, jobs: List[Dict[str, Any]]) -> List[JobResult]:
        """
        执行一批任务
        
        Args:
            jobs: 任务列表，每个任务格式为 {'id': str, 'data': Any}
        
        Returns:
            执行结果列表
        """
        pass
    
    @abstractmethod
    def shutdown(self, timeout: float = 5.0) -> None:
        """
        关闭执行器，释放资源
        
        Args:
            timeout: 等待超时时间（秒）
        """
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取执行统计信息（可选实现）
        
        Returns:
            统计信息字典
        """
        return {}
