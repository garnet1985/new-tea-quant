#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
多线程执行器（基于 concurrent.futures）

这是 MultiThreadWorker 的 Executor 接口包装（原 FuturesWorker）
"""

from typing import Any, Callable, Dict, List, Optional

from .base import Executor, JobResult

# 导入多线程 Worker（原 FuturesWorker）
from ..multi_thread.futures_worker import MultiThreadWorker, ExecutionMode


class MultiThreadExecutor(Executor):
    """
    多线程执行器
    
    基于 concurrent.futures.ThreadPoolExecutor 实现
    """
    
    def __init__(
        self,
        max_workers: int = 5,
        execution_mode: ExecutionMode = ExecutionMode.PARALLEL,
        job_executor: Optional[Callable] = None,
        timeout: float = 30.0,
        is_verbose: bool = False,
    ):
        """
        初始化
        
        Args:
            max_workers: 最大并行工作线程数
            execution_mode: 执行模式（串行/并行）
            job_executor: 自定义任务执行函数
            timeout: 任务超时时间（秒）
            is_verbose: 是否启用详细日志输出
        """
        self._worker = MultiThreadWorker(
            max_workers=max_workers,
            execution_mode=execution_mode,
            job_executor=job_executor,
            timeout=timeout,
            is_verbose=is_verbose,
        )
    
    def run_jobs(self, jobs: List[Dict[str, Any]]) -> List[JobResult]:
        """
        执行一批任务
        
        Args:
            jobs: 任务列表，每个任务格式为 {'id': str, 'data': Any}
        
        Returns:
            执行结果列表
        """
        # 使用原有的 FuturesWorker 执行
        self._worker.run_jobs(jobs)
        return self._worker.get_results()
    
    def shutdown(self, timeout: float = 5.0) -> None:
        """关闭执行器，释放资源"""
        self._worker.shutdown(timeout=timeout)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取执行统计信息"""
        return self._worker.get_stats()
