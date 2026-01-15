#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
内存感知调度器

基于内存监控数据动态调整 batch size
"""

import logging
from typing import Any, Iterable, List, Optional, Union

from .base import Scheduler
from ..monitors.memory_monitor import MemoryMonitor, _get_available_memory_mb


def _auto_calculate_memory_budget_mb() -> float:
    """自动计算内存预算"""
    available = _get_available_memory_mb()
    budget = available * 0.7
    return max(1024.0, min(budget, 16384.0))


def _auto_calculate_batch_sizes(total_jobs: int) -> tuple[int, int, int]:
    """根据任务总数自动计算合理的 batch 大小"""
    if total_jobs <= 0:
        return (20, 10, 500)
    
    if total_jobs < 100:
        warmup = min(10, total_jobs // 2)
        min_size = max(5, warmup // 2)
        max_size = min(100, total_jobs)
    elif total_jobs < 1000:
        warmup = 20
        min_size = 10
        max_size = 200
    else:
        warmup = 30
        min_size = 10
        max_size = 500
    
    return (warmup, min_size, max_size)

logger = logging.getLogger(__name__)


class MemoryAwareScheduler(Scheduler):
    """
    内存感知调度器
    
    职责：
    - 基于内存监控数据动态调整 batch size
    - 使用 MemoryMonitor 进行内存观测
    """
    
    def __init__(
        self,
        jobs: List[Any],
        memory_budget_mb: Union[float, str, None] = "auto",
        warmup_batch_size: Union[int, str] = "auto",
        min_batch_size: Union[int, str] = "auto",
        max_batch_size: Union[int, str] = "auto",
        smooth_factor: float = 0.3,
        summary_weight: float = 0.2,
        monitor_interval: int = 5,
        log: Optional[logging.Logger] = None,
    ):
        """
        初始化调度器
        
        Args:
            jobs: 原始任务列表
            memory_budget_mb: 内存预算（MB），"auto" 表示自动计算
            warmup_batch_size: 初始批次大小，"auto" 表示自动计算
            min_batch_size: 最小批次大小，"auto" 表示自动计算
            max_batch_size: 最大批次大小，"auto" 表示自动计算
            smooth_factor: 指数平滑系数
            summary_weight: 汇总信息占比
            monitor_interval: 监控日志输出间隔
            log: 可选 logger
        """
        self.jobs: List[Any] = list(jobs)
        self.total_jobs: int = len(self.jobs)
        
        # 自动计算或使用提供的值
        if memory_budget_mb == "auto" or memory_budget_mb is None:
            memory_budget = _auto_calculate_memory_budget_mb()
            if log:
                log.info(f"📊 自动计算内存预算: {memory_budget:.1f} MB")
        else:
            memory_budget = max(float(memory_budget_mb), 1.0)
        
        # 自动计算 batch sizes
        if warmup_batch_size == "auto" or min_batch_size == "auto" or max_batch_size == "auto":
            auto_warmup, auto_min, auto_max = _auto_calculate_batch_sizes(self.total_jobs)
            self.warmup_batch_size = auto_warmup if warmup_batch_size == "auto" else max(int(warmup_batch_size), 1)
            self.min_batch_size = auto_min if min_batch_size == "auto" else max(int(min_batch_size), 1)
            self.max_batch_size = auto_max if max_batch_size == "auto" else max(int(max_batch_size), self.min_batch_size)
            if log:
                log.info(
                    f"📊 自动计算 batch sizes: warmup={self.warmup_batch_size}, "
                    f"min={self.min_batch_size}, max={self.max_batch_size}"
                )
        else:
            self.warmup_batch_size = max(int(warmup_batch_size), 1)
            self.min_batch_size = max(int(min_batch_size), 1)
            self.max_batch_size = max(int(max_batch_size), self.min_batch_size)
        
        self.smooth_factor = float(smooth_factor)
        self.summary_weight = float(summary_weight)
        self.monitor_interval = max(int(monitor_interval), 1)
        self.log = log or logger
        
        # 创建内存监控器
        self.monitor = MemoryMonitor(
            memory_budget_mb=memory_budget,
        )
        
        # 调度状态
        if self.total_jobs == 0:
            self.current_batch_size = 0
        else:
            initial = min(self.warmup_batch_size, self.total_jobs)
            self.current_batch_size = max(initial, self.min_batch_size)
        
        self._cursor = 0
        self.finished_jobs = 0
        self._batch_index = 0
        self._total_failed_jobs = 0
    
    def iter_batches(self) -> Iterable[List[Any]]:
        """
        迭代批次
        
        Yields:
            批次任务列表
        """
        if self.total_jobs == 0:
            return
        
        while self._cursor < self.total_jobs:
            batch_size = min(self.current_batch_size, self.total_jobs - self._cursor)
            if batch_size <= 0:
                break
            
            # 记录批次开始时的内存
            self.monitor.record_batch_start()
            
            start = self._cursor
            end = start + batch_size
            batch = self.jobs[start:end]
            
            self._cursor = end
            self._batch_index += 1
            
            yield batch
    
    def get_next_batch_size(self) -> int:
        """获取下一批的批次大小"""
        return self.current_batch_size
    
    def update_after_batch(
        self,
        batch_size: int,
        batch_results: List[Any],
        finished_jobs: int,
    ) -> None:
        """在批次执行完成后更新调度器状态"""
        self.finished_jobs = finished_jobs
        
        # 统计失败任务数量
        failed_in_batch = 0
        for r in batch_results:
            try:
                status = getattr(r, "status", None) or getattr(r, "job_status", None)
                status_value = getattr(status, "value", str(status))
                if isinstance(status_value, str) and status_value.lower() in ("failed", "error"):
                    failed_in_batch += 1
            except Exception:
                continue
        
        self._total_failed_jobs += failed_in_batch
        
        # 获取批次内存增量
        delta_batch = self.monitor.get_batch_delta_mb()
        
        # 更新监控器
        self.monitor.update(
            batch_size=batch_size,
            delta_batch_mb=delta_batch,
            finished_jobs=finished_jobs,
            smooth_factor=self.smooth_factor,
            summary_weight=self.summary_weight,
        )
        
        # 根据监控数据调整 batch size
        self._adjust_batch_size()
    
    def _adjust_batch_size(self) -> None:
        """根据当前内存估算和已完成任务数调整 batch size"""
        if self.total_jobs <= 0:
            self.current_batch_size = 0
            return
        
        stats = self.monitor.get_stats()
        available_for_working_mb = stats.get("working_set_available_mb", 1.0)
        mem_working_per_job = stats.get("mem_working_per_job", 0.0)
        
        if mem_working_per_job > 0.0:
            target_batch = int(available_for_working_mb / mem_working_per_job)
        else:
            target_batch = self.current_batch_size or self.min_batch_size
        
        # clamp 到合法区间
        target_batch = max(self.min_batch_size, min(target_batch, self.max_batch_size))
        
        # 限制单次调整幅度
        current = self.current_batch_size or self.min_batch_size
        max_step = max(int(current * 0.5), 5)
        delta = target_batch - current
        if delta > max_step:
            delta = max_step
        elif delta < -max_step:
            delta = -max_step
        
        self.current_batch_size = max(self.min_batch_size, min(current + delta, self.max_batch_size))
    
    def get_monitor_stats(self) -> dict:
        """获取监控统计信息（兼容旧接口）"""
        memory_stats = self.monitor.get_stats()
        total_jobs = max(self.total_jobs, 1)
        finished = max(min(self.finished_jobs, total_jobs), 0)
        progress_percent = finished / total_jobs * 100.0
        
        failure_rate = (self._total_failed_jobs / float(finished)) * 100.0 if finished > 0 else 0.0
        
        usage_percent = memory_stats.get("usage_percent", 0.0)
        memory_warning = usage_percent >= 90.0
        health_status = "healthy"
        if memory_warning:
            health_status = "critical"
        elif usage_percent >= 75.0:
            health_status = "warning"
        
        return {
            "memory": memory_stats,
            "progress": {
                "total_jobs": total_jobs,
                "finished_jobs": finished,
                "current_batch": self._batch_index,
                "progress_percent": progress_percent,
            },
            "performance": {
                "current_batch_size": self.current_batch_size,
            },
            "health": {
                "memory_warning": memory_warning,
                "failure_rate": failure_rate,
                "status": health_status,
            },
        }

    def get_progress(self) -> dict:
        """
        获取简化的进度信息（友好的 Progress API）

        Returns:
            {
                'total_jobs': int,
                'finished_jobs': int,
                'progress_percent': float,
                'current_batch_index': int,
                'current_batch_size': int,
            }
        """
        total_jobs = max(self.total_jobs, 1)
        finished = max(min(self.finished_jobs, total_jobs), 0)
        progress_percent = finished / total_jobs * 100.0

        return {
            "total_jobs": total_jobs,
            "finished_jobs": finished,
            "progress_percent": progress_percent,
            "current_batch_index": self._batch_index,
            "current_batch_size": self.current_batch_size,
        }
    
    def get_memory_warning(self) -> Optional[str]:
        """获取内存告警信息"""
        warnings = self.monitor.get_warnings()
        return warnings[0] if warnings else None
    
    def should_log_progress(self) -> bool:
        """判断是否应该输出进度日志"""
        if self._batch_index == 0:
            return False
        if self.finished_jobs >= self.total_jobs:
            return True
        return (self._batch_index % self.monitor_interval) == 0
    
    def reset(self) -> None:
        """重置调度器状态"""
        self._cursor = 0
        self.finished_jobs = 0
        self._batch_index = 0
        self._total_failed_jobs = 0
