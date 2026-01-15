#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Memory-Aware Batch Scheduler

一个围绕现有 Worker（FuturesWorker / ProcessWorker）的轻量级调度与监控组件：

- 按批（batch）调度 jobs，避免一次把所有任务推给执行器；
- 基于进程 RSS 内存占用动态调整 batch size，减少 OOM 风险；
- 收集基础监控指标（内存 / 进度 / 简单性能），可作为 Worker 的 monitor。

注意：
- 这是一个纯 Python 组件，不依赖具体的 Worker 实现；
- Executor 只需要能接受一批 jobs 并返回对应的结果；
- 调用方负责在每个 batch 执行完成后调用 `update_after_batch`。
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Union

import psutil


logger = logging.getLogger(__name__)


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


def _auto_calculate_memory_budget_mb() -> float:
    """
    自动计算内存预算。
    
    策略：
    - 获取系统可用内存
    - 预留 30% 给系统和其他进程
    - 返回剩余 70% 作为预算
    """
    available = _get_available_memory_mb()
    # 预留 30% 给系统，使用 70%
    budget = available * 0.7
    # 至少保证 1GB，最多不超过 16GB（避免在超大内存机器上过度使用）
    return max(1024.0, min(budget, 16384.0))


def _auto_calculate_batch_sizes(total_jobs: int) -> tuple[int, int, int]:
    """
    根据任务总数自动计算合理的 batch 大小。
    
    Returns:
        (warmup_batch_size, min_batch_size, max_batch_size)
    """
    if total_jobs <= 0:
        return (20, 10, 500)
    
    # 根据任务总数动态调整
    if total_jobs < 100:
        # 小规模：较小的 batch
        warmup = min(10, total_jobs // 2)
        min_size = max(5, warmup // 2)
        max_size = min(100, total_jobs)
    elif total_jobs < 1000:
        # 中等规模：中等 batch
        warmup = 20
        min_size = 10
        max_size = 200
    else:
        # 大规模：较大的 batch
        warmup = 30
        min_size = 10
        max_size = 500
    
    return (warmup, min_size, max_size)


@dataclass
class BatchMonitorStats:
    """单次调度周期内的监控快照。"""

    memory: Dict[str, Any] = field(default_factory=dict)
    progress: Dict[str, Any] = field(default_factory=dict)
    performance: Dict[str, Any] = field(default_factory=dict)
    health: Dict[str, Any] = field(default_factory=dict)


class MemoryAwareBatchScheduler:
    """
    基于内存感知的批量调度器 + 简单监控器。

    典型使用方式（伪代码）::

        scheduler = MemoryAwareBatchScheduler(jobs, memory_budget_mb=5000.0)

        finished_jobs = 0
        all_results = []

        for batch in scheduler.iter_batches():
            worker = FuturesWorker(...)
            worker_jobs = [{'id': j['id'], 'data': j} for j in batch]
            worker.run_jobs(worker_jobs)
            batch_results = worker.get_results()

            finished_jobs += len(batch)
            scheduler.update_after_batch(
                batch_size=len(batch),
                batch_results=batch_results,
                finished_jobs=finished_jobs,
            )

            all_results.extend(batch_results)

            if scheduler.should_log_progress():
                stats = scheduler.get_monitor_stats()
                logger.info("进度: %.1f%%, 内存: %.1f%%, batch_size=%d",
                            stats["progress"]["progress_percent"],
                            stats["memory"]["usage_percent"],
                            stats["performance"]["current_batch_size"])
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
    ) -> None:
        """
        初始化调度器。

        Args:
            jobs: 原始任务列表（如股票 ID 列表或 payload 列表）。
            memory_budget_mb: 为整个执行过程预留的额外内存预算（MB）。
                - "auto": 自动计算（系统可用内存的 70%，至少 1GB，最多 16GB）
                - 数字: 手动指定（MB）
            warmup_batch_size: 首批 job 数量，用于估算 mem_per_job。
                - "auto": 根据任务总数自动计算
                - 数字: 手动指定
            min_batch_size: 最小 batch 大小。
                - "auto": 根据任务总数自动计算
                - 数字: 手动指定
            max_batch_size: 最大 batch 大小。
                - "auto": 根据任务总数自动计算
                - 数字: 手动指定
            smooth_factor: 指数平滑系数（0~1），用于平滑 mem_per_job 估算。
            summary_weight: 单 job 内存增量中，被视为“汇总信息”的占比（0~1）。
            monitor_interval: 每多少个 batch 输出一次监控日志（由调用方决定是否使用）。
            log: 可选 logger，默认使用本模块 logger。
        """
        self.jobs: List[Any] = list(jobs)
        self.total_jobs: int = len(self.jobs)

        # 自动计算或使用提供的值
        if memory_budget_mb == "auto" or memory_budget_mb is None:
            self.memory_budget_mb = _auto_calculate_memory_budget_mb()
            if log:
                log.info(f"📊 自动计算内存预算: {self.memory_budget_mb:.1f} MB")
        else:
            self.memory_budget_mb = max(float(memory_budget_mb), 1.0)

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
        self.smooth_factor: float = float(smooth_factor)
        self.summary_weight: float = float(summary_weight)
        self.monitor_interval: int = max(int(monitor_interval), 1)

        self.log: logging.Logger = log or logger

        # 内存估算相关
        self.mem_working_per_job: float = 0.0
        self.mem_summary_per_job: float = 0.0
        self._baseline_rss_mb: float = _get_rss_mb()
        self._last_batch_mem_before: Optional[float] = None

        # 调度状态
        if self.total_jobs == 0:
            self.current_batch_size: int = 0
        else:
            initial = min(self.warmup_batch_size, self.total_jobs)
            self.current_batch_size = max(initial, self.min_batch_size)

        self._cursor: int = 0
        self.finished_jobs: int = 0
        self._batch_index: int = 0
        self._total_failed_jobs: int = 0

        # 监控快照
        self._last_stats: BatchMonitorStats = BatchMonitorStats()

    # ------------------------------------------------------------------
    # 调度接口
    # ------------------------------------------------------------------
    def iter_batches(self) -> Iterable[List[Any]]:
        """
        以当前的 batch size 依次返回子列表。

        注意：
        - 在每次 yield 之前，会记录当前 RSS 用于后续 delta 计算；
        - 调用方在处理完该 batch 后，应调用 `update_after_batch`。
        """
        if self.total_jobs == 0:
            return

        while self._cursor < self.total_jobs:
            # 控制本批大小不超过剩余任务数
            batch_size = min(self.current_batch_size, self.total_jobs - self._cursor)
            if batch_size <= 0:
                break

            self._last_batch_mem_before = _get_rss_mb()

            start = self._cursor
            end = start + batch_size
            batch = self.jobs[start:end]

            self._cursor = end
            self._batch_index += 1

            yield batch

    def update_after_batch(
        self,
        batch_size: int,
        batch_results: List[Any],
        finished_jobs: int,
    ) -> None:
        """
        在每个 batch 执行完成后调用，用于：
        - 更新内存估算；
        - 动态调整下一批的 batch size；
        - 刷新监控统计。
        """
        self.finished_jobs = finished_jobs

        # 统计失败任务数量（如果结果对象有类似 status 字段）
        failed_in_batch = 0
        for r in batch_results:
            try:
                status = getattr(r, "status", None) or getattr(r, "job_status", None)
                status_value = getattr(status, "value", str(status))
                if isinstance(status_value, str) and status_value.lower() in ("failed", "error"):
                    failed_in_batch += 1
            except Exception:
                # 结果格式不符合预期时，不影响主流程
                continue

        self._total_failed_jobs += failed_in_batch

        # 内存增量观测
        mem_after = _get_rss_mb()
        if self._last_batch_mem_before is not None:
            delta_batch = max(mem_after - self._last_batch_mem_before, 0.0)
        else:
            delta_batch = 0.0

        # 更新 per-job 内存估算
        if batch_size > 0 and delta_batch > 0.0:
            mem_per_job_obs = delta_batch / float(batch_size)
            mem_summary_per_job = mem_per_job_obs * self.summary_weight
            mem_working_per_job = max(mem_per_job_obs - mem_summary_per_job, 0.0)

            if self.mem_working_per_job <= 0.0:
                # 首次观测，直接赋值
                self.mem_working_per_job = mem_working_per_job
                self.mem_summary_per_job = mem_summary_per_job
            else:
                # 指数平滑
                s = self.smooth_factor
                self.mem_working_per_job = (
                    self.mem_working_per_job * (1.0 - s) + mem_working_per_job * s
                )
                self.mem_summary_per_job = (
                    self.mem_summary_per_job * (1.0 - s) + mem_summary_per_job * s
                )

        # 根据估算结果调整下一批 batch size
        self._adjust_batch_size()

        # 刷新监控快照
        self._refresh_monitor_stats(current_rss_mb=mem_after)

    # ------------------------------------------------------------------
    # 内部：batch size 调整逻辑
    # ------------------------------------------------------------------
    def _adjust_batch_size(self) -> None:
        """根据当前内存估算和已完成任务数调整 batch size。"""
        if self.total_jobs <= 0:
            self.current_batch_size = 0
            return

        # 估算汇总信息已占用的内存
        summary_used_mb = max(
            self.finished_jobs * self.mem_summary_per_job,
            0.0,
        )
        # 为工作集预留的可用内存
        available_for_working_mb = max(
            self.memory_budget_mb - summary_used_mb,
            1.0,  # 至少留一点空间，避免为 0 或负数
        )

        if self.mem_working_per_job > 0.0:
            target_batch = int(available_for_working_mb / self.mem_working_per_job)
        else:
            # 还无法估算时，保持当前 batch 大小
            target_batch = self.current_batch_size or self.min_batch_size

        # clamp 到合法区间
        target_batch = max(self.min_batch_size, min(target_batch, self.max_batch_size))

        # 限制单次调整幅度，避免抖动过大
        current = self.current_batch_size or self.min_batch_size
        max_step = max(int(current * 0.5), 5)
        delta = target_batch - current
        if delta > max_step:
            delta = max_step
        elif delta < -max_step:
            delta = -max_step

        new_batch_size = max(self.min_batch_size, min(current + delta, self.max_batch_size))
        self.current_batch_size = new_batch_size

    # ------------------------------------------------------------------
    # 监控接口
    # ------------------------------------------------------------------
    def _refresh_monitor_stats(self, current_rss_mb: Optional[float] = None) -> None:
        """更新监控快照。"""
        if current_rss_mb is None:
            current_rss_mb = _get_rss_mb()

        used_mb = max(current_rss_mb - self._baseline_rss_mb, 0.0)
        usage_percent = (used_mb / self.memory_budget_mb * 100.0) if self.memory_budget_mb > 0 else 0.0

        total_jobs = max(self.total_jobs, 1)
        finished = max(min(self.finished_jobs, total_jobs), 0)
        progress_percent = finished / total_jobs * 100.0

        failure_rate = (self._total_failed_jobs / float(finished)) * 100.0 if finished > 0 else 0.0

        memory_warning = usage_percent >= 90.0 or used_mb >= self.memory_budget_mb
        health_status = "healthy"
        if memory_warning:
            health_status = "critical"
        elif usage_percent >= 75.0:
            health_status = "warning"

        self._last_stats = BatchMonitorStats(
            memory={
                "current_rss_mb": current_rss_mb,
                "memory_budget_mb": self.memory_budget_mb,
                "used_mb": used_mb,
                "available_mb": max(self.memory_budget_mb - used_mb, 0.0),
                "usage_percent": usage_percent,
                "summary_used_mb": max(self.finished_jobs * self.mem_summary_per_job, 0.0),
            },
            progress={
                "total_jobs": total_jobs,
                "finished_jobs": finished,
                "current_batch": self._batch_index,
                "total_batches_estimated": (total_jobs + max(self.current_batch_size, 1) - 1)
                // max(self.current_batch_size, 1),
                "progress_percent": progress_percent,
            },
            performance={
                # 这里仅记录当前 batch size，具体耗时由上层根据业务需要自行计算
                "current_batch_size": self.current_batch_size,
            },
            health={
                "memory_warning": memory_warning,
                "failure_rate": failure_rate,
                "status": health_status,
            },
        )

    def get_monitor_stats(self) -> Dict[str, Any]:
        """获取最近一次更新后的监控统计信息。"""
        # 若尚未执行任何 batch，则先刷新一次
        if self._batch_index == 0:
            self._refresh_monitor_stats()

        return {
            "memory": dict(self._last_stats.memory),
            "progress": dict(self._last_stats.progress),
            "performance": dict(self._last_stats.performance),
            "health": dict(self._last_stats.health),
        }

    def get_memory_warning(self) -> Optional[str]:
        """如有内存告警，返回告警信息，否则返回 None。"""
        stats = self.get_monitor_stats()
        memory = stats["memory"]
        health = stats["health"]

        if not health.get("memory_warning"):
            return None

        return (
            f"内存接近或超过预算: "
            f"used={memory.get('used_mb', 0):.1f}MB / "
            f"budget={memory.get('memory_budget_mb', 0):.1f}MB "
            f"({memory.get('usage_percent', 0):.1f}%)"
        )

    def should_log_progress(self) -> bool:
        """
        简单的进度日志节流策略：
        - 每 monitor_interval 个 batch 输出一次；
        - 或者在全部完成时输出一次。
        """
        if self._batch_index == 0:
            return False

        if self.finished_jobs >= self.total_jobs:
            return True

        return (self._batch_index % self.monitor_interval) == 0

