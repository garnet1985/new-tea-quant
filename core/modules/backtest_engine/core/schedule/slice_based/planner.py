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

from core.infra.machine_capacity import MachineCapacity, MachineInfo
from core.modules.backtest_engine.core.shared.jobs import BacktestJob
from core.modules.backtest_engine.core.shared.types import JobContext
from core.modules.backtest_engine.core.shared.base_planner import BasePlanner
from core.modules.backtest_engine.core.performance.settings import SliceBasedPerformance
from core.modules.backtest_engine.core.schedule.slice_based.monitor import (
    SliceMonitorConfig,
    SliceMonitorPlanSnapshot,
)
from core.modules.backtest_engine.core.schedule.slice_based.probe import (
    SliceProbe,
    SliceProbeResult,
)
from core.modules.backtest_engine.core.schedule.slice_based.preload import (
    MAX_PRELOAD_DEPTH,
    resolve_preload_depth,
)
from core.modules.backtest_engine.core.performance.settings import DEFAULT_PRELOAD_DEPTH

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SliceDispatchPlan:
    """切片调度规划（Step 3结果）。"""
    
    # Reader配置
    reader_workers: int
    reader_memory_budget_mb: float
    
    # Compute配置
    compute_processes: int  # 通常为1（单进程）；报告侧别名 compute_workers
    compute_memory_budget_mb: float
    
    # 队列配置：queue_capacity 与 preload_depth 同值（单一名：preload_depth）
    queue_capacity: int
    preload_depth: int
    
    # Slice配置
    slice_open_days: int
    dispatch_jobs: int  # 报告侧别名 total_slices
    
    # 内存管理
    memory_budget_mb: float
    oom_adjusted: bool

    # 探针快照（供 performance 报告；可选）
    probe: Optional[Dict[str, Any]] = None


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
        """Skeleton plan before execute.

        Head-phase sampling (first N formal slices) runs during execute and
        counts toward official output; see ``refine_plan_from_probe`` /
        ``SliceExecutePipeline``.
        """
        _ = execute_fn
        _ = executor
        capacity = cls._get_machine_capacity(performance)

        provisional_days = performance.get("slice_open_days")
        if provisional_days in (None, "", "auto"):
            provisional_days = 20
        else:
            provisional_days = int(provisional_days)

        sample_head = SliceProbe.should_run(jobs, performance)

        resolved_performance = SliceBasedPerformance.resolve_for_planning(
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
        resolved_performance["_sample_head_slices"] = sample_head

        # Skeleton only — preload provisional until head samples refine it.
        plan = cls._resolve_slice_plan(
            jobs, capacity, None, resolved_performance, log_label
        )
        batches = cls._split_slice_batches(jobs, plan)
        head_n = SliceProbe.head_slice_count(resolved_performance) if sample_head else 0
        annotated: List[SliceJobBatch] = []
        for batch in batches:
            payload = SliceProbe.annotate_payload_for_head_sampling(
                batch.payload,
                slice_open_days=plan.slice_open_days,
                probe_slice_count=head_n,
                sample_enabled=sample_head,
            )
            annotated.append(
                SliceJobBatch(
                    batch_id=batch.batch_id,
                    slice_ids=list(batch.slice_ids),
                    slices_count=batch.slices_count,
                    payload=payload,
                )
            )
        monitor_config = cls._build_monitor(plan, resolved_performance)
        if sample_head:
            logger.info(
                "%s骨架规划完成；执行时采样前 %s 片（全 entity，片宽=%s）计入输出",
                log_label,
                head_n,
                plan.slice_open_days,
            )
        else:
            logger.info("%s跳过 head 采样（配置已固定 preload/staged）", log_label)
        return plan, annotated, monitor_config

    @classmethod
    def refine_plan_from_probe(
        cls,
        plan: SliceDispatchPlan,
        probe_result: Optional[SliceProbeResult],
        capacity: MachineCapacity,
        performance: Dict[str, Any],
        log_label: str = "切片调度",
    ) -> SliceDispatchPlan:
        """Recompute preload_depth from head samples; keep reader_workers fixed."""
        if probe_result is None or int(probe_result.slices_sampled or 0) <= 0:
            return plan

        available_memory_mb = MachineInfo.worker_pool_budget_mb(capacity)
        mb_in_flight = max(
            1.0,
            float(probe_result.mb_per_slice_reader)
            + float(probe_result.mb_per_slice_payload),
        )
        raw_depth = performance.get("preload_depth")
        if raw_depth in (None, "", "auto"):
            preload_depth = resolve_preload_depth(
                t_io_sec=probe_result.sec_per_slice_reader,
                t_compute_sec=probe_result.sec_per_slice_compute,
                memory_budget_mb=available_memory_mb,
                mb_per_in_flight_slice=mb_in_flight,
                prefetch_enabled=bool(performance.get("prefetch_enabled", True)),
            )
        else:
            preload_depth = max(1, min(MAX_PRELOAD_DEPTH, int(raw_depth)))

        base = SliceDispatchPlan(
            reader_workers=plan.reader_workers,
            reader_memory_budget_mb=0.0,
            compute_processes=plan.compute_processes,
            compute_memory_budget_mb=probe_result.mb_per_slice_compute,
            queue_capacity=preload_depth,
            preload_depth=preload_depth,
            slice_open_days=plan.slice_open_days,
            dispatch_jobs=plan.dispatch_jobs,
            memory_budget_mb=plan.memory_budget_mb,
            oom_adjusted=False,
            probe=None,
        )
        refined = cls._apply_oom_protection(base, capacity, probe_result)
        probe_snap = cls._probe_to_dict(probe_result)
        from dataclasses import replace

        refined = replace(refined, probe=probe_snap)
        logger.info(
            "%shead 采样 refine: preload_depth=%s (=queue), readers=%s, "
            "sec_read=%.3f sec_compute=%.3f slices=%s",
            log_label,
            refined.preload_depth,
            refined.reader_workers,
            probe_result.sec_per_slice_reader,
            probe_result.sec_per_slice_compute,
            probe_result.slices_sampled,
        )
        return refined

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

        # 始终挂 probe 快照：真探针或 OOM 使用的默认单价（报告可回填 estimated）
        probe_snap = cls._probe_to_dict(probe_result)
        if probe_snap is None:
            probe_snap = {
                "ran": False,
                "source": "plan_defaults",
                "slices_sampled": 0,
                "mb_per_slice_reader": 10.0,
                "mb_per_slice_compute": 15.0,
                "mb_per_slice_payload": 5.0,
                "sec_per_slice_reader": 0.0,
                "sec_per_slice_compute": 0.0,
                "sec_per_slice_serialize": 0.0,
                "sec_per_slice_deserialize": 0.0,
                "peak_rss_mb_reader": 0.0,
                "peak_rss_mb_compute": 0.0,
                "wall_sec": 0.0,
            }
        from dataclasses import replace

        final_plan = replace(final_plan, probe=probe_snap)
        
        logger.info(
            "%s规划: reader_workers=%s (standby), compute_processes=%s, "
            "preload_depth=%s (=queue), slice_days=%s, jobs=%s, oom=%s, probe=%s",
            log_label,
            final_plan.reader_workers,
            final_plan.compute_processes,
            final_plan.preload_depth,
            final_plan.slice_open_days,
            final_plan.dispatch_jobs,
            final_plan.oom_adjusted,
            "ran" if probe_snap.get("ran") else probe_snap.get("source", "none"),
        )
        
        return final_plan

    @staticmethod
    def _probe_to_dict(probe_result: Optional[SliceProbeResult]) -> Optional[Dict[str, Any]]:
        if probe_result is None:
            return None
        return {
            "ran": True,
            "source": "probe",
            "slices_sampled": int(probe_result.slices_sampled),
            "mb_per_slice_reader": float(probe_result.mb_per_slice_reader),
            "mb_per_slice_compute": float(probe_result.mb_per_slice_compute),
            "mb_per_slice_payload": float(probe_result.mb_per_slice_payload),
            "sec_per_slice_reader": float(probe_result.sec_per_slice_reader),
            "sec_per_slice_compute": float(probe_result.sec_per_slice_compute),
            "sec_per_slice_serialize": float(probe_result.sec_per_slice_serialize),
            "sec_per_slice_deserialize": float(probe_result.sec_per_slice_deserialize),
            "peak_rss_mb_reader": float(probe_result.peak_rss_mb_reader),
            "peak_rss_mb_compute": float(probe_result.peak_rss_mb_compute),
            "wall_sec": float(probe_result.wall_sec),
        }
    
    @classmethod
    def _resolve_base_plan(
        cls,
        jobs: List[Dict[str, Any]],
        capacity: MachineCapacity,
        probe_result: Optional[SliceProbeResult],
        performance: Dict[str, Any],
    ) -> SliceDispatchPlan:
        """计算基础规划（不考虑 OOM 二次砍深度）。

        Reader = fixed standby pool. ``preload_depth`` (= ``queue_capacity``)
        comes from ``t_io / t_compute`` then memory clip when still auto.
        """
        slice_open_days = int(performance.get("slice_open_days", 20))
        total_slices = cls._count_calendar_slices(jobs, slice_open_days)
        reader_workers = max(1, int(performance.get("reader_workers", 1)))
        compute_processes = int(performance.get("compute_processes", 1))
        prefetch_enabled = bool(performance.get("prefetch_enabled", True))
        available_memory_mb = MachineInfo.worker_pool_budget_mb(capacity)

        mb_reader = probe_result.mb_per_slice_reader if probe_result else 10.0
        mb_payload = probe_result.mb_per_slice_payload if probe_result else 5.0
        mb_compute = probe_result.mb_per_slice_compute if probe_result else 15.0
        # Standby model: in-flight cost ≈ one reader slice + one queued payload
        mb_in_flight = max(1.0, mb_reader + mb_payload)

        raw_depth = performance.get("preload_depth")
        if raw_depth in (None, "", "auto"):
            t_io = probe_result.sec_per_slice_reader if probe_result else None
            t_compute = probe_result.sec_per_slice_compute if probe_result else None
            preload_depth = resolve_preload_depth(
                t_io_sec=t_io,
                t_compute_sec=t_compute,
                memory_budget_mb=available_memory_mb,
                mb_per_in_flight_slice=mb_in_flight,
                prefetch_enabled=prefetch_enabled,
            )
            if probe_result is None and prefetch_enabled:
                preload_depth = min(preload_depth, DEFAULT_PRELOAD_DEPTH)
        else:
            preload_depth = max(1, min(MAX_PRELOAD_DEPTH, int(raw_depth)))
            if not prefetch_enabled:
                preload_depth = 1

        # Unified name: queue_capacity always equals preload_depth
        queue_capacity = preload_depth
        dispatch_jobs = max(1, total_slices)

        return SliceDispatchPlan(
            reader_workers=reader_workers,
            reader_memory_budget_mb=0.0,  # filled in OOM pass
            compute_processes=compute_processes,
            compute_memory_budget_mb=mb_compute,
            queue_capacity=queue_capacity,
            preload_depth=preload_depth,
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
        """OOM 保护：只砍 ``preload_depth``（= queue），不砍 standby readers。

        Resident estimate (standby pool)::

            preload_depth * (mb_reader + mb_payload) + mb_compute
        """
        available_memory_mb = MachineInfo.worker_pool_budget_mb(capacity)

        mb_per_slice_reader = probe_result.mb_per_slice_reader if probe_result else 10.0
        mb_per_slice_compute = probe_result.mb_per_slice_compute if probe_result else 15.0
        mb_per_slice_payload = probe_result.mb_per_slice_payload if probe_result else 5.0
        mb_in_flight = max(1.0, mb_per_slice_reader + mb_per_slice_payload)

        reader_workers = base_plan.reader_workers
        preload_depth = base_plan.preload_depth
        compute_memory_mb = mb_per_slice_compute

        def _total(depth: int) -> float:
            return depth * mb_in_flight + compute_memory_mb

        total_memory_mb = _total(preload_depth)
        oom_adjusted = False

        if total_memory_mb > available_memory_mb:
            max_depth = max(
                1,
                min(
                    MAX_PRELOAD_DEPTH,
                    int((available_memory_mb - compute_memory_mb) / mb_in_flight),
                ),
            )
            if preload_depth > max_depth:
                logger.warning(
                    "OOM保护: preload_depth %s→%s (readers fixed=%s; "
                    "估内存 %.1fMB→%.1fMB, 可用=%.1fMB)",
                    preload_depth,
                    max_depth,
                    reader_workers,
                    total_memory_mb,
                    _total(max_depth),
                    available_memory_mb,
                )
                preload_depth = max_depth
                oom_adjusted = True

        reader_memory_mb = preload_depth * mb_per_slice_reader
        payload_memory_mb = preload_depth * mb_per_slice_payload
        final_memory_mb = reader_memory_mb + payload_memory_mb + compute_memory_mb

        if final_memory_mb > available_memory_mb:
            logger.error(
                "OOM保护后仍超预算: 最终使用=%.1fMB > 可用=%.1fMB",
                final_memory_mb,
                available_memory_mb,
            )

        return SliceDispatchPlan(
            reader_workers=reader_workers,
            reader_memory_budget_mb=reader_memory_mb,
            compute_processes=base_plan.compute_processes,
            compute_memory_budget_mb=compute_memory_mb,
            queue_capacity=preload_depth,
            preload_depth=preload_depth,
            slice_open_days=base_plan.slice_open_days,
            dispatch_jobs=base_plan.dispatch_jobs,
            memory_budget_mb=capacity.memory_budget_mb,
            oom_adjusted=oom_adjusted,
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
        """单 bulk job + entity_ids + timeline_point_count：calendar_slice 形态。"""
        if len(jobs) != 1:
            return False
        payload = BacktestJob.from_dict(jobs[0]).payload
        entity_ids = payload.get(BacktestJob.SLICE_BASED_ENTITY_KEY)
        if not isinstance(entity_ids, list) or not entity_ids:
            return False
        point_count = payload.get(BacktestJob.TIMELINE_POINT_COUNT_KEY)
        return isinstance(point_count, int) and point_count > 0

    @classmethod
    def _count_calendar_slices(cls, jobs: List[Dict[str, Any]], slice_open_days: int) -> int:
        if not jobs:
            return 0

        days = max(1, int(slice_open_days))
        payload = BacktestJob.from_dict(jobs[0]).payload
        point_count = payload.get(BacktestJob.TIMELINE_POINT_COUNT_KEY)
        if isinstance(point_count, int) and point_count > 0:
            return max(1, math.ceil(point_count / days))

        if len(jobs) > 1:
            return len(jobs)
        return 1


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