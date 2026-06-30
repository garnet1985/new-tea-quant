"""
Backtest Engine - Slice-based Planner

切片模式的调度规划器（读算分离）。

职责：
- 获取机器容量（共享machine_info）
- slice探针测量（读算分离内存）
- 制定读算分离规划（reader_workers、queue_capacity等）
- 切割slice jobs
- 更严格的OOM管控

特点：
- 读算分离（Reader多进程 + Compute单进程）
- 管道队列控制（queue_capacity）
- 更容易OOM，需要严格管控
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.modules.backtest_engine.core.shared.machine_info import MachineCapacity, MachineInfo
from core.modules.backtest_engine.core.shared.jobs import BacktestJob
from core.modules.backtest_engine.core.shared.types import JobContext
from core.modules.backtest_engine.core.shared.base_planner import BasePlanner
from core.modules.backtest_engine.core.slice_based.config import SliceConfig
from core.modules.backtest_engine.core.slice_based.monitor import (
    SliceMonitorConfig,
    SliceMonitorPlanSnapshot,
)
from core.modules.backtest_engine.core.slice_based.probe import (
    SliceProbe,
    SliceProbeResult,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SliceDispatchPlan:
    """切片调度规划（Step 3结果）。"""
    
    # Reader配置
    reader_workers: int
    reader_memory_budget_mb: float
    
    # Compute配置
    compute_processes: int  # 通常为1（单进程）
    compute_memory_budget_mb: float
    
    # 队列配置
    queue_capacity: int
    preload_depth: int
    
    # Slice配置
    slice_open_days: int
    dispatch_jobs: int
    
    # 内存管理
    memory_budget_mb: float
    oom_adjusted: bool


@dataclass(frozen=True)
class SliceJobBatch:
    """切割后的切片job批次（Step 4结果）。"""
    
    batch_id: str
    slice_ids: List[str]  # 日期切片列表
    slices_count: int
    payload: Dict[str, Any]


class SlicePlanner(BasePlanner):
    """切片模式调度规划器（读算分离）。
    
    继承BasePlanner，自由实现内部逻辑：
    - Reader多进程 + Compute单进程
    - 管道队列控制
    - 更严格的OOM管控
    """
    
    @classmethod
    def plan_jobs(
        cls,
        jobs: List[Dict[str, Any]],
        performance: Dict[str, Any],
        *,
        execute_fn: Optional[Callable[[JobContext], Dict[str, Any]]] = None,
        executor: Optional[str] = None,
        log_label: str = "切片调度",
    ) -> Tuple[SliceDispatchPlan, List[SliceJobBatch], SliceMonitorConfig]:
        """Planner的编排层（对外API）。
        
        Args:
            jobs: 待执行的job列表
            performance: 配置字典
            executor: 执行器
            log_label: 日志标签
            
        Returns:
            Tuple[SliceDispatchPlan, List[SliceJobBatch]]: 规划结果和切片批次
        """
        # 1. 获取机器容量（共享）
        capacity = cls._get_machine_capacity(performance)

        provisional_days = performance.get("slice_open_days")
        if provisional_days in (None, "", "auto"):
            provisional_days = 20
        else:
            provisional_days = int(provisional_days)

        resolved_performance = SliceConfig.normalize_for_planning(
            performance,
            capacity,
            dispatch_slices=cls._count_calendar_slices(jobs, provisional_days),
        )
        dispatch_slices = cls._count_calendar_slices(
            jobs,
            int(resolved_performance["slice_open_days"]),
        )
        if dispatch_slices > 0:
            resolved_performance = dict(resolved_performance)
            resolved_performance["_dispatch_slices"] = dispatch_slices

        # 2. slice探针测量（读算分离内存）
        probe_result = cls._measure_slice_probe(
            jobs, capacity, resolved_performance, execute_fn, log_label
        )

        # 3. 制定读算分离规划（reader_workers、queue_capacity等）
        plan = cls._resolve_slice_plan(
            jobs, capacity, probe_result, resolved_performance, log_label
        )
        
        # 4. 切割slice jobs
        batches = cls._split_slice_batches(jobs, plan)

        monitor_config = cls._build_monitor(plan, resolved_performance)

        return plan, batches, monitor_config
    
    @classmethod
    def _measure_slice_probe(
        cls,
        jobs: List[Dict[str, Any]],
        capacity: MachineCapacity,
        performance: Dict[str, Any],
        execute_fn: Optional[Callable[[JobContext], Dict[str, Any]]],
        log_label: str,
    ) -> Optional[SliceProbeResult]:
        """slice探针测量（读算分离内存）。
        
        Args:
            jobs: 待执行的job列表
            capacity: 机器容量
            performance: 配置字典
            executor: 执行器
            log_label: 日志标签
            
        Returns:
            Optional[SliceProbeResult]: 探针结果
        """
        # 检查是否需要探针
        if not SliceProbe.should_run(jobs, performance):
            logger.info("%s跳过探针（用户指定配置）", log_label)
            return None
        
        # 构建探针jobs
        probe_jobs = SliceProbe.build_probe_jobs(jobs, capacity, performance)
        
        # 执行探针
        return SliceProbe.dispatch(
            probe_jobs,
            execute_fn=execute_fn,
            performance=performance,
            log_label=log_label,
        )
    
    @classmethod
    def _resolve_slice_plan(
        cls,
        jobs: List[Dict[str, Any]],
        capacity: MachineCapacity,
        probe_result: Optional[SliceProbeResult],
        performance: Dict[str, Any],
        log_label: str,
    ) -> SliceDispatchPlan:
        """制定读算分离规划。
        
        Args:
            jobs: 待执行的job列表
            capacity: 机器容量
            probe_result: 探针结果
            performance: 配置字典
            log_label: 日志标签
            
        Returns:
            SliceDispatchPlan: 切片调度规划
        """
        # 3.1: 计算基础规划（reader_workers、queue_capacity等）
        base_plan = cls._resolve_base_plan(jobs, capacity, probe_result, performance)
        
        # 3.2: OOM保护（更严格的管控）
        final_plan = cls._apply_oom_protection(base_plan, capacity, probe_result)
        
        logger.info(
            "%s规划: reader_workers=%s, compute_processes=%s, queue=%s, "
            "preload=%s, slice_days=%s, jobs=%s, oom=%s",
            log_label,
            final_plan.reader_workers,
            final_plan.compute_processes,
            final_plan.queue_capacity,
            final_plan.preload_depth,
            final_plan.slice_open_days,
            final_plan.dispatch_jobs,
            final_plan.oom_adjusted,
        )
        
        return final_plan
    
    @classmethod
    def _resolve_base_plan(
        cls,
        jobs: List[Dict[str, Any]],
        capacity: MachineCapacity,
        probe_result: Optional[SliceProbeResult],
        performance: Dict[str, Any],
    ) -> SliceDispatchPlan:
        """计算基础规划（不考虑OOM）。
        
        Args:
            jobs: 待执行的job列表
            capacity: 机器容量
            probe_result: 探针结果
            performance: 配置字典
            
        Returns:
            SliceDispatchPlan: 基础规划
        """
        slice_open_days = int(performance.get("slice_open_days", 20))
        total_slices = cls._count_calendar_slices(jobs, slice_open_days)

        reader_workers_base = int(performance.get("reader_workers", 2))
        
        # Compute processes（单进程）
        compute_processes = int(performance.get("compute_processes", 1))
        
        # Queue capacity（管道队列控制）
        queue_capacity_base = int(performance.get("queue_capacity", 10))
        
        # Preload depth（预加载深度）
        preload_depth_base = int(performance.get("preload_depth", 2))
        
        dispatch_jobs = max(1, total_slices)
        
        return SliceDispatchPlan(
            reader_workers=reader_workers_base,
            reader_memory_budget_mb=0.0,  # TODO: 根据探针计算
            compute_processes=compute_processes,
            compute_memory_budget_mb=0.0,  # TODO: 根据探针计算
            queue_capacity=queue_capacity_base,
            preload_depth=preload_depth_base,
            slice_open_days=slice_open_days,
            dispatch_jobs=dispatch_jobs,
            memory_budget_mb=capacity.memory_budget_mb,
            oom_adjusted=False,
        )
    
    @classmethod
    def _apply_oom_protection(
        cls,
        base_plan: SliceDispatchPlan,
        capacity: MachineCapacity,
        probe_result: Optional[SliceProbeResult],
    ) -> SliceDispatchPlan:
        """OOM保护（更严格的管控）。
        
        根据探针结果计算内存使用：
        - Reader内存：reader_workers * mb_per_slice_reader * preload_depth
        - Compute内存：mb_per_slice_compute（单进程）
        - Payload内存：queue_capacity * mb_per_slice_payload
        
        Args:
            base_plan: 基础规划
            capacity: 机器容量
            probe_result: 探针结果
            
        Returns:
            SliceDispatchPlan: 最终规划（OOM保护后）
        """
        available_memory_mb = MachineInfo.worker_pool_budget_mb(capacity)
        
        # 根据探针结果计算内存消耗（如果没有探针，使用默认值）
        mb_per_slice_reader = probe_result.mb_per_slice_reader if probe_result else 10.0
        mb_per_slice_compute = probe_result.mb_per_slice_compute if probe_result else 15.0
        mb_per_slice_payload = probe_result.mb_per_slice_payload if probe_result else 5.0
        
        # 计算当前内存使用
        reader_memory_mb = base_plan.reader_workers * mb_per_slice_reader * base_plan.preload_depth
        compute_memory_mb = mb_per_slice_compute
        payload_memory_mb = base_plan.queue_capacity * mb_per_slice_payload
        total_memory_mb = reader_memory_mb + compute_memory_mb + payload_memory_mb
        
        # 检查OOM风险
        if total_memory_mb <= available_memory_mb:
            # 没有OOM风险，直接返回基础规划
            return SliceDispatchPlan(
                reader_workers=base_plan.reader_workers,
                reader_memory_budget_mb=reader_memory_mb,
                compute_processes=base_plan.compute_processes,
                compute_memory_budget_mb=compute_memory_mb,
                queue_capacity=base_plan.queue_capacity,
                preload_depth=base_plan.preload_depth,
                slice_open_days=base_plan.slice_open_days,
                dispatch_jobs=base_plan.dispatch_jobs,
                memory_budget_mb=capacity.memory_budget_mb,
                oom_adjusted=False,
            )
        
        # OOM风险，调整规划
        logger.warning(
            "OOM风险检测: 当前使用=%.1fMB, 可用=%.1fMB, 调整规划...",
            total_memory_mb,
            available_memory_mb,
        )
        
        # 调整策略：优先降低reader_workers，再降低queue_capacity和preload_depth
        reader_workers = base_plan.reader_workers
        queue_capacity = base_plan.queue_capacity
        preload_depth = base_plan.preload_depth
        
        # Step 1: 降低reader_workers（Reader占大头）
        max_reader_workers_by_memory = int(
            (available_memory_mb - compute_memory_mb - payload_memory_mb) 
            / (mb_per_slice_reader * preload_depth)
        )
        if reader_workers > max_reader_workers_by_memory:
            reader_workers = max(1, max_reader_workers_by_memory)
        
        # Step 2: 降低queue_capacity（Payload内存）
        max_queue_capacity_by_memory = int(
            (available_memory_mb - reader_workers * mb_per_slice_reader * preload_depth - compute_memory_mb)
            / mb_per_slice_payload
        )
        if queue_capacity > max_queue_capacity_by_memory:
            queue_capacity = max(1, min(max_queue_capacity_by_memory, preload_depth * 2))
        
        # Step 3: 降低preload_depth（进一步降低Reader内存）
        max_preload_depth_by_memory = int(
            (available_memory_mb - compute_memory_mb - queue_capacity * mb_per_slice_payload)
            / (reader_workers * mb_per_slice_reader)
        )
        if preload_depth > max_preload_depth_by_memory:
            preload_depth = max(1, min(max_preload_depth_by_memory, queue_capacity))
        
        # 再次检查内存使用
        reader_memory_mb = reader_workers * mb_per_slice_reader * preload_depth
        compute_memory_mb = mb_per_slice_compute
        payload_memory_mb = queue_capacity * mb_per_slice_payload
        final_memory_mb = reader_memory_mb + compute_memory_mb + payload_memory_mb
        
        if final_memory_mb > available_memory_mb:
            logger.error(
                "OOM保护失败: 最终使用=%.1fMB > 可用=%.1fMB，无法满足",
                final_memory_mb,
                available_memory_mb,
            )
        
        logger.info(
            "OOM保护: reader_workers %s→%s, queue %s→%s, preload %s→%s "
            "(内存 %.1fMB→%.1fMB)",
            base_plan.reader_workers,
            reader_workers,
            base_plan.queue_capacity,
            queue_capacity,
            base_plan.preload_depth,
            preload_depth,
            total_memory_mb,
            final_memory_mb,
        )
        
        return SliceDispatchPlan(
            reader_workers=reader_workers,
            reader_memory_budget_mb=reader_memory_mb,
            compute_processes=base_plan.compute_processes,
            compute_memory_budget_mb=compute_memory_mb,
            queue_capacity=queue_capacity,
            preload_depth=preload_depth,
            slice_open_days=base_plan.slice_open_days,
            dispatch_jobs=base_plan.dispatch_jobs,
            memory_budget_mb=capacity.memory_budget_mb,
            oom_adjusted=True,
        )
    
    @classmethod
    def _split_slice_batches(
        cls,
        jobs: List[Dict[str, Any]],
        plan: SliceDispatchPlan,
    ) -> List[SliceJobBatch]:
        """切割slice jobs。
        
        根据slice_open_days切割日期切片：
        - 每个batch包含多个slice（slice_open_days天）
        - slice_id为日期范围
        
        Args:
            jobs: 待执行的job列表
            plan: 切片调度规划
            
        Returns:
            List[SliceJobBatch]: 切割后的切片批次
        """
        if not jobs:
            return []

        if cls._is_bulk_calendar_job(jobs):
            parsed = BacktestJob.from_dict(jobs[0])
            job_id, payload = parsed.id, parsed.payload
            slice_ids = [
                f"slice_{index}"
                for index in range(plan.dispatch_jobs)
            ]
            batch = SliceJobBatch(
                batch_id=job_id,
                slice_ids=slice_ids,
                slices_count=plan.dispatch_jobs,
                payload=dict(payload),
            )
            logger.info(
                "切割完成: bulk job=%s, expected_slices=%s, batches=1",
                job_id,
                plan.dispatch_jobs,
            )
            return [batch]

        batches: List[SliceJobBatch] = []
        for index, job in enumerate(jobs):
            parsed = BacktestJob.from_dict(job)
            job_id, payload = parsed.id, parsed.payload
            slice_id = str(payload.get("slice_id") or job_id)
            batches.append(
                SliceJobBatch(
                    batch_id=job_id,
                    slice_ids=[slice_id],
                    slices_count=1,
                    payload=dict(payload),
                )
            )

        logger.info(
            "切割完成: slices=%s, batches=%s",
            len(jobs),
            len(batches),
        )
        return batches

    @classmethod
    def _is_bulk_calendar_job(cls, jobs: List[Dict[str, Any]]) -> bool:
        """单 bulk job + 日历 open_dates：calendar_slice 形态（与具体业务模块无关）。"""
        if len(jobs) != 1:
            return False
        payload = BacktestJob.from_dict(jobs[0]).payload
        if not cls._resolve_open_dates(jobs):
            return False
        bulk_keys = ("entity_ids", "entities", "stock_ids", "entity_id", "stock_id")
        return any(payload.get(key) for key in bulk_keys)

    @classmethod
    def _count_calendar_slices(cls, jobs: List[Dict[str, Any]], slice_open_days: int) -> int:
        if not jobs:
            return 0

        days = max(1, int(slice_open_days))
        open_dates = cls._resolve_open_dates(jobs)
        if open_dates:
            return max(1, math.ceil(len(open_dates) / days))

        if len(jobs) > 1:
            return len(jobs)
        return 1

    @classmethod
    def _resolve_open_dates(cls, jobs: List[Dict[str, Any]]) -> List[str]:
        payload = BacktestJob.from_dict(jobs[0]).payload
        open_dates = payload.get("open_dates")
        if isinstance(open_dates, list) and open_dates:
            return [str(d) for d in open_dates if str(d).strip()]

        calendar = payload.get("backtest_calendar")
        if isinstance(calendar, dict):
            calendar_dates = calendar.get("open_dates")
            if isinstance(calendar_dates, list) and calendar_dates:
                return [str(d) for d in calendar_dates if str(d).strip()]
        return []


    @staticmethod
    def _build_monitor(
        plan: SliceDispatchPlan,
        performance: Dict[str, Any],
    ) -> SliceMonitorConfig:
        payload_memory_budget_mb = max(
            1.0,
            plan.memory_budget_mb
            - plan.reader_memory_budget_mb
            - plan.compute_memory_budget_mb,
        )
        snapshot = SliceMonitorPlanSnapshot(
            reader_workers=plan.reader_workers,
            queue_capacity=plan.queue_capacity,
            preload_depth=plan.preload_depth,
            slice_open_days=plan.slice_open_days,
            dispatch_slices=plan.dispatch_jobs,
            reader_memory_budget_mb=plan.reader_memory_budget_mb,
            compute_memory_budget_mb=plan.compute_memory_budget_mb,
            payload_memory_budget_mb=payload_memory_budget_mb,
            memory_budget_mb=plan.memory_budget_mb,
        )
        return SliceMonitorConfig.from_dispatch_plan(snapshot, performance)


__all__ = [
    "SliceDispatchPlan",
    "SliceJobBatch",
    "SlicePlanner",
]