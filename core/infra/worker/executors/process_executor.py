#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
多进程执行器（基于 multiprocessing）

这是 ProcessWorker 的 Executor 接口包装
"""

from typing import Any, Callable, Dict, List, Optional

from .base import Executor, JobResult

# 导入原有的 ProcessWorker（暂时保留，后续可以逐步迁移）
# 注意：executors 与 multi_process 同级，当前模块包为 app.core.infra.worker.executors
# 因此使用 ..multi_process 指向 app.core.infra.worker.multi_process
from ..multi_process.process_worker import ProcessWorker as _ProcessWorker, ExecutionMode


class ProcessExecutor(Executor):
    """
    多进程执行器
    
    基于 multiprocessing.ProcessPoolExecutor 实现
    """
    
    def __init__(
        self,
        max_workers: Optional[int] = None,
        execution_mode: ExecutionMode = ExecutionMode.QUEUE,
        job_executor: Optional[Callable] = None,
        is_verbose: bool = False,
    ):
        """
        初始化
        
        Args:
            max_workers: 最大并行工作进程数（None 表示自动）
            execution_mode: 执行模式（BATCH/QUEUE）
            job_executor: 自定义任务执行函数
            is_verbose: 是否启用详细日志输出
        """
        self._worker = _ProcessWorker(
            max_workers=max_workers,
            execution_mode=execution_mode,
            job_executor=job_executor,
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
        # 使用原有的 ProcessWorker 执行
        self._worker.run_jobs(jobs)
        return self._worker.get_results()
    
    def shutdown(self, timeout: float = 5.0) -> None:
        """关闭执行器，释放资源"""
        # ProcessWorker 没有 shutdown 方法，这里只是占位符
        # 实际的清理在 ProcessPoolExecutor 的上下文管理器中自动完成
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """获取执行统计信息"""
        return self._worker.get_stats()
