#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
内存监控器

负责观测进程内存使用情况，提供内存相关的监控指标和告警
"""

import os
from typing import Any, Dict, List, Optional

import psutil

from .base import Monitor


def _get_rss_mb() -> float:
    """获取当前进程 RSS 内存，单位 MB。"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)


def _get_available_memory_mb() -> float:
    """获取系统可用内存，单位 MB。"""
    try:
        mem = psutil.virtual_memory()
        # 返回可用内存（available），如果不可用则用 free
        return mem.available / (1024 * 1024) if hasattr(mem, 'available') else mem.free / (1024 * 1024)
    except Exception:
        # 如果获取失败，返回一个保守的默认值（4GB）
        return 4096.0


class MemoryMonitor(Monitor):
    """
    内存监控器
    
    职责：
    - 观测进程 RSS 内存占用
    - 计算内存增量
    - 提供内存告警
    """
    
    def __init__(
        self,
        memory_budget_mb: float,
        baseline_rss_mb: Optional[float] = None,
    ):
        """
        初始化
        
        Args:
            memory_budget_mb: 内存预算（MB）
            baseline_rss_mb: 基线 RSS 内存（MB），如果为 None 则自动获取当前值
        """
        self.memory_budget_mb = float(memory_budget_mb)
        self._baseline_rss_mb = baseline_rss_mb if baseline_rss_mb is not None else _get_rss_mb()
        self._current_rss_mb = self._baseline_rss_mb
        self._last_batch_mem_before: Optional[float] = None
        
        # 内存估算相关
        self.mem_working_per_job: float = 0.0
        self.mem_summary_per_job: float = 0.0
        self.finished_jobs: int = 0
    
    def update(
        self,
        current_rss_mb: Optional[float] = None,
        batch_size: int = 0,
        delta_batch_mb: float = 0.0,
        finished_jobs: int = 0,
        smooth_factor: float = 0.3,
        summary_weight: float = 0.2,
    ) -> None:
        """
        更新监控状态
        
        Args:
            current_rss_mb: 当前 RSS 内存（MB），如果为 None 则自动获取
            batch_size: 批次大小
            delta_batch_mb: 批次内存增量（MB）
            finished_jobs: 已完成的任务数
            smooth_factor: 指数平滑系数
            summary_weight: 汇总信息占比
        """
        if current_rss_mb is not None:
            self._current_rss_mb = current_rss_mb
        else:
            self._current_rss_mb = _get_rss_mb()
        
        self.finished_jobs = finished_jobs
        
        # 更新 per-job 内存估算
        if batch_size > 0 and delta_batch_mb > 0.0:
            mem_per_job_obs = delta_batch_mb / float(batch_size)
            mem_summary_per_job = mem_per_job_obs * summary_weight
            mem_working_per_job = max(mem_per_job_obs - mem_summary_per_job, 0.0)
            
            if self.mem_working_per_job <= 0.0:
                # 首次观测，直接赋值
                self.mem_working_per_job = mem_working_per_job
                self.mem_summary_per_job = mem_summary_per_job
            else:
                # 指数平滑
                s = smooth_factor
                self.mem_working_per_job = (
                    self.mem_working_per_job * (1.0 - s) + mem_working_per_job * s
                )
                self.mem_summary_per_job = (
                    self.mem_summary_per_job * (1.0 - s) + mem_summary_per_job * s
                )
    
    def record_batch_start(self) -> None:
        """记录批次开始时的内存"""
        self._last_batch_mem_before = _get_rss_mb()
    
    def get_batch_delta_mb(self) -> float:
        """获取批次内存增量（MB）"""
        if self._last_batch_mem_before is None:
            return 0.0
        current = _get_rss_mb()
        return max(current - self._last_batch_mem_before, 0.0)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取监控统计信息"""
        used_mb = max(self._current_rss_mb - self._baseline_rss_mb, 0.0)
        usage_percent = (used_mb / self.memory_budget_mb * 100.0) if self.memory_budget_mb > 0 else 0.0
        summary_used_mb = max(self.finished_jobs * self.mem_summary_per_job, 0.0)
        
        return {
            "current_rss_mb": self._current_rss_mb,
            "memory_budget_mb": self.memory_budget_mb,
            "used_mb": used_mb,
            "available_mb": max(self.memory_budget_mb - used_mb, 0.0),
            "usage_percent": usage_percent,
            "summary_used_mb": summary_used_mb,
            "working_set_available_mb": max(self.memory_budget_mb - summary_used_mb, 0.0),
            "mem_working_per_job": self.mem_working_per_job,
            "mem_summary_per_job": self.mem_summary_per_job,
        }
    
    def get_warnings(self) -> List[str]:
        """获取告警信息"""
        warnings = []
        stats = self.get_stats()
        
        usage_percent = stats.get("usage_percent", 0.0)
        used_mb = stats.get("used_mb", 0.0)
        
        if usage_percent >= 90.0 or used_mb >= self.memory_budget_mb:
            warnings.append(
                f"内存接近或超过预算: "
                f"used={used_mb:.1f}MB / "
                f"budget={self.memory_budget_mb:.1f}MB "
                f"({usage_percent:.1f}%)"
            )
        elif usage_percent >= 75.0:
            warnings.append(
                f"内存使用率较高: {usage_percent:.1f}% "
                f"({used_mb:.1f}MB / {self.memory_budget_mb:.1f}MB)"
            )
        
        return warnings
    
    def export_snapshot(self) -> Dict[str, Any]:
        """导出监控快照"""
        return {
            "timestamp": os.times().elapsed if hasattr(os.times(), 'elapsed') else 0.0,
            "stats": self.get_stats(),
            "warnings": self.get_warnings(),
        }
