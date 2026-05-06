#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
多进程执行器（基于 multiprocessing）

这是 ProcessWorker 的 Executor 接口包装
"""

from typing import Any, Callable, Dict, List, Optional

from .base import Executor, JobResult

# 导入原有的 ProcessWorker（暂时保留，后续可以逐步迁移）
# 注意：executors 与 multi_process 同级，当前模块包为 core.infra.worker.executors
# 因此使用 ..multi_process 指向 core.infra.worker.multi_process
from ..multi_process.process_worker import (
    ProcessWorker as _ProcessWorker,
    ExecutionMode,
    ProgressReportConfig,
)


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
        on_job_done: Optional[Callable[[Dict[str, Any]], None]] = None,
        progress_report_config: Optional[ProgressReportConfig] = None,
        is_main_process_used_if_single_worker: bool = True,
        is_verbose: bool = False,
    ):
        """
        初始化
        
        Args:
            max_workers: 最大并行工作进程数（None 表示自动）
            execution_mode: 执行模式（BATCH/QUEUE）
            job_executor: 自定义任务执行函数
            on_job_done: 每个 job 完成时的回调（可选）
            progress_report_config: 进度日志上报配置（可选）
            is_main_process_used_if_single_worker: 当 max_workers=1 时，是否使用主进程串行执行（默认 True）
            is_verbose: 是否启用详细日志输出
        """
        self._worker = _ProcessWorker(
            max_workers=max_workers,
            execution_mode=execution_mode,
            job_executor=job_executor,
            on_job_done=on_job_done,
            progress_report_config=progress_report_config,
            is_main_process_used_if_single_worker=is_main_process_used_if_single_worker,
            is_verbose=is_verbose,
        )
    
    def run_jobs(self, jobs: List[Dict[str, Any]], total_jobs: Optional[int] = None) -> List[JobResult]:
        """
        执行一批任务
        
        Args:
            jobs: 任务列表，每个任务格式为 {'id': str, 'data': Any}
            total_jobs: 总任务数（用于进度跟踪）。如果提供，将使用此值而不是当前批次的大小
                      这对于分批执行时保持准确的进度跟踪很重要
        
        Returns:
            执行结果列表
        """
        # 使用原有的 ProcessWorker 执行
        self._worker.run_jobs(jobs, total_jobs=total_jobs)
        return self._worker.get_results()
    
    def shutdown(self, timeout: float = 5.0) -> None:
        """关闭执行器，释放资源"""
        # ProcessWorker 没有 shutdown 方法，这里只是占位符
        # 实际的清理在 ProcessPoolExecutor 的上下文管理器中自动完成
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """获取执行统计信息"""
        return self._worker.get_stats()
