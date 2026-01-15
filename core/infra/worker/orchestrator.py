#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
编排器（Orchestrator）

组合所有组件，提供统一的高级 API
"""

from typing import Any, Callable, Dict, List, Optional

from .executors.base import Executor, JobResult
from .queues.base import JobSource
from .monitors.base import Monitor
from .schedulers.base import Scheduler
from .aggregators.base import Aggregator
from .error_handlers.base import ErrorHandler, ErrorAction


class Orchestrator:
    """
    编排器
    
    职责：组合所有组件，提供统一的高级 API
    """
    
    def __init__(
        self,
        executor: Executor,
        job_source: JobSource,
        scheduler: Optional[Scheduler] = None,
        monitor: Optional[Monitor] = None,
        aggregator: Optional[Aggregator] = None,
        error_handler: Optional[ErrorHandler] = None,
    ):
        """
        初始化编排器
        
        Args:
            executor: 执行器
            job_source: 任务源
            scheduler: 调度器（可选）
            monitor: 监控器（可选）
            aggregator: 聚合器（可选）
            error_handler: 错误处理器（可选）
        """
        self.executor = executor
        self.job_source = job_source
        self.scheduler = scheduler
        self.monitor = monitor
        self.aggregator = aggregator
        self.error_handler = error_handler
    
    def run(self) -> Dict[str, Any]:
        """
        执行所有任务
        
        Returns:
            执行结果汇总
        """
        all_results: List[JobResult] = []
        
        # 如果有调度器，使用调度器控制批次大小
        if self.scheduler:
            # 假设 scheduler 有 iter_batches 方法（MemoryAwareScheduler 的特殊接口）
            if hasattr(self.scheduler, 'iter_batches'):
                for batch in self.scheduler.iter_batches():
                    batch_results = self._execute_batch(batch)
                    all_results.extend(batch_results)
                    
                    # 更新调度器
                    finished_jobs = len(all_results)
                    self.scheduler.update_after_batch(
                        batch_size=len(batch),
                        batch_results=batch_results,
                        finished_jobs=finished_jobs,
                    )
            else:
                # 使用调度器的 get_next_batch_size
                while self.job_source.has_more():
                    batch_size = self.scheduler.get_next_batch_size()
                    batch = self.job_source.get_batch(batch_size)
                    if not batch:
                        break
                    
                    batch_results = self._execute_batch(batch)
                    all_results.extend(batch_results)
                    
                    # 更新调度器
                    finished_jobs = len(all_results)
                    self.scheduler.update_after_batch(
                        batch_size=len(batch),
                        batch_results=batch_results,
                        finished_jobs=finished_jobs,
                    )
        else:
            # 没有调度器，直接执行所有任务
            while self.job_source.has_more():
                batch = self.job_source.get_batch(1000)  # 默认批次大小
                if not batch:
                    break
                
                batch_results = self._execute_batch(batch)
                all_results.extend(batch_results)
        
        # 聚合结果
        summary = {}
        if self.aggregator:
            for result in all_results:
                self.aggregator.add_result(result)
            summary = self.aggregator.get_summary()
        
        # 添加监控信息
        if self.monitor:
            summary['monitor_stats'] = self.monitor.get_stats()
            summary['warnings'] = self.monitor.get_warnings()
        
        return {
            'results': all_results,
            'summary': summary,
        }
    
    def _execute_batch(self, batch: List[Any]) -> List[JobResult]:
        """执行一批任务"""
        # 将任务转换为 Executor 格式
        jobs = []
        for job in batch:
            if isinstance(job, dict):
                jobs.append(job)
            else:
                # 如果不是字典，尝试转换
                jobs.append({'id': str(job), 'data': job})
        
        # 执行任务
        results = self.executor.run_jobs(jobs)
        
        # 处理错误
        if self.error_handler:
            for result in results:
                if result.status.value == 'failed' and result.error:
                    action = self.error_handler.handle_error(
                        job={'id': result.job_id, 'data': None},
                        error=result.error,
                    )
                    # 根据 action 决定是否重试等（简化实现）
                    if action == ErrorAction.ABORT:
                        raise RuntimeError(f"Error handler requested abort: {result.error}")
        
        return results
    
    def shutdown(self) -> None:
        """关闭所有组件"""
        self.executor.shutdown()
        if self.monitor:
            # Monitor 通常不需要显式关闭
            pass
