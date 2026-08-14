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

from core.infra.machine_capacity import MachineInfo
from core.infra.machine_capacity.contracts import MachineCapacity
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
from core.modules.backtest_engine.core.schedule.slice_based.slice_width import (
    SliceMemoryPlan,
    SliceMemoryPlanner,
    SliceWidthError,
)

logger = logging.getLogger(__name__)

_DEFAULT_MB_PER_OPEN_DAY = 1.0
_DEFAULT_MB_PER_SLICE_READER = 10.0
_DEFAULT_MB_PER_SLICE_PAYLOAD = 5.0
_DEFAULT_MB_PER_SLICE_COMPUTE = 15.0
# Provisional only when callers skip ``_resolve_memory_plan`` (tests / skeleton).
_DEFAULT_PRELOAD_DEPTH = 0


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

    # Lookback / readiness（与 Strategy settings 对齐，由 plan 写入）
    min_required_records: int = 20

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
        load_per_entity_window: Optional[Callable[..., Dict[str, Any]]] = None,
    ) -> Tuple[SliceDispatchPlan, List[SliceJobBatch], SliceMonitorConfig]:
        """Skeleton plan before execute.

        Head-phase sampling (first N formal slices) runs during execute and
        counts toward official output; see ``refine_plan_from_probe`` /
        ``SliceExecutePipeline``.
        """
        _ = execute_fn
        _ = executor
        capacity = cls._get_machine_capacity(performance)

        raw_days = performance.get("slice_open_days")
        is_auto_width = raw_days in (None, "", "auto")
        min_required = SliceMemoryPlanner.default_min_required(
            performance.get("min_required_records")
        )
        provisional_days = (
            min_required if is_auto_width else max(1, int(raw_days))
        )

        sample_head = SliceProbe.should_run(jobs, performance)

        resolved_performance = SliceBasedPerformance.resolve_for_planning(
            performance,
            capacity,
            dispatch_slices=cls._count_calendar_slices(jobs, provisional_days),
        )
        resolved_performance = dict(resolved_performance)
        resolved_performance["min_required_records"] = min_required
        for key in ("mb_per_open_day", "probe_mb"):
            if key in performance and performance.get(key) not in (None, ""):
                resolved_performance[key] = performance[key]

        if SliceProbe.needs_memory_probe(resolved_performance):
            if not jobs:
                # 无 job 时不探针；后续走默认 mb_per_open_day
                pass
            else:
                try:
                    resolved_performance["probe_mb"] = SliceProbe.measure_probe_mb(
                        jobs,
                        min_required=min_required,
                        load_per_entity_window=load_per_entity_window,
                    )
                except Exception as exc:
                    # Do not fall back to a tiny default MB/day — that inflates width
                    # (e.g. 5000 entities → hundreds of open days per slice).
                    logger.error("%s内存探针失败: %s", log_label, exc)
                    raise SliceWidthError(
                        f"slice 内存探针失败，拒绝用默认单价规划片宽: {exc}"
                    ) from exc

        try:
            mem_plan = cls._resolve_memory_plan(
                capacity,
                resolved_performance,
                is_auto_width=bool(
                    resolved_performance.get("_slice_open_days_auto", is_auto_width)
                ),
                explicit_width=None if is_auto_width else int(raw_days),
            )
        except SliceWidthError as exc:
            logger.error("%s片宽决议失败: %s", log_label, exc)
            raise

        resolved_performance["slice_open_days"] = mem_plan.slice_open_days
        resolved_performance["reader_workers"] = mem_plan.reader_workers
        resolved_performance["preload_depth"] = mem_plan.queue_depth
        resolved_performance["queue_capacity"] = mem_plan.queue_depth
        resolved_performance["queue_depth"] = mem_plan.queue_depth
        resolved_performance["compute_processes"] = SliceMemoryPlanner.COMPUTE_PROCESSES
        resolved_performance["mb_per_open_day"] = mem_plan.mb_per_open_day
        resolved_performance["_peak_slices"] = mem_plan.peak_slices
        resolved_performance["_compute_slices"] = mem_plan.compute_slices

        dispatch_slices = cls._count_calendar_slices(
            jobs,
            int(resolved_performance["slice_open_days"]),
        )
        if dispatch_slices > 0:
            resolved_performance["_dispatch_slices"] = dispatch_slices
        resolved_performance["_sample_head_slices"] = sample_head

        # Skeleton only — queue may refine after real slices.
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
            logger.info(
                "%s跳过 head 采样（dispatch_probe 关闭或 preload_depth 已固定）",
                log_label,
            )
        return plan, annotated, monitor_config

    @classmethod
    def _resolve_memory_plan(
        cls,
        capacity: MachineCapacity,
        performance: Dict[str, Any],
        *,
        is_auto_width: bool,
        explicit_width: Optional[int],
    ) -> SliceMemoryPlan:
        """Resolve width + R + N per SLICE_BASED_ALGORITHM.md."""
        available_mb = float(MachineInfo.worker_pool_budget_mb(capacity))
        min_required = SliceMemoryPlanner.default_min_required(
            performance.get("min_required_records")
        )
        reserve = int(getattr(capacity, "reserve_cores", 1) or 1)
        cpu = int(getattr(capacity, "cpu_count", 1) or 1)

        probe_mb = performance.get("probe_mb")
        mb_per_day = performance.get("mb_per_open_day")
        if probe_mb not in (None, ""):
            mem_plan = SliceMemoryPlanner.resolve_initial(
                budget_mb=available_mb,
                probe_mb=float(probe_mb),
                probe_width=min_required,
                cpu_count=cpu,
                reserve_cores=reserve,
                min_required=min_required,
            )
        else:
            per = (
                max(float(mb_per_day), 1e-6)
                if mb_per_day not in (None, "")
                else _DEFAULT_MB_PER_OPEN_DAY
            )
            mem_plan = SliceMemoryPlanner.resolve_from_unit_cost(
                budget_mb=available_mb,
                mb_per_open_day=per,
                cpu_count=cpu,
                reserve_cores=reserve,
                min_required=min_required,
            )

        if not is_auto_width and explicit_width is not None:
            width = max(1, int(explicit_width))
            if width < min_required:
                raise SliceWidthError(
                    f"显式片宽 {width} < min_required={min_required}"
                )
            # Keep R/N from memory plan; re-check peak with explicit width.
            slice_mb = width * mem_plan.mb_per_open_day
            need = mem_plan.peak_slices * slice_mb
            if need > available_mb * SliceMemoryPlanner.SAFETY:
                raise SliceWidthError(
                    f"显式片宽 {width} 在 peak_slices={mem_plan.peak_slices} 下超预算："
                    f"need={need:.1f}MB > budget*{SliceMemoryPlanner.SAFETY}"
                    f"={available_mb * SliceMemoryPlanner.SAFETY:.1f}MB"
                )
            from dataclasses import replace

            mem_plan = replace(mem_plan, slice_open_days=width)

        logger.info(
            "片宽决议: width=%s queue=%s readers=%s peak_slices=%s "
            "min_required=%s mb_per_open_day=%.4f budget_mb=%.1f",
            mem_plan.slice_open_days,
            mem_plan.queue_depth,
            mem_plan.reader_workers,
            mem_plan.peak_slices,
            mem_plan.min_required,
            mem_plan.mb_per_open_day,
            mem_plan.budget_mb,
        )
        return mem_plan

    @classmethod
    def refine_plan_from_probe(
        cls,
        plan: SliceDispatchPlan,
        probe_result: Optional[SliceProbeResult],
        capacity: MachineCapacity,
        performance: Dict[str, Any],
        log_label: str = "切片调度",
    ) -> SliceDispatchPlan:
        """Refine queue_depth from real slice timings; keep slice_open_days fixed."""
        if probe_result is None or int(probe_result.slices_sampled or 0) <= 0:
            return plan

        available_memory_mb = MachineInfo.worker_pool_budget_mb(capacity)
        mb_per_slice = max(
            1.0,
            float(probe_result.mb_per_slice_reader)
            + float(probe_result.mb_per_slice_payload),
        )
        raw_depth = performance.get("preload_depth")
        if raw_depth in (None, "", "auto"):
            preload_depth = SliceMemoryPlanner.refine_queue_depth(
                budget_mb=available_memory_mb,
                mb_per_slice=mb_per_slice,
                reader_workers=plan.reader_workers,
                current_queue=plan.preload_depth,
                t_load_sec=float(probe_result.sec_per_slice_reader),
                t_compute_sec=float(probe_result.sec_per_slice_compute),
            )
        else:
            preload_depth = max(0, int(raw_depth))

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
            oom_adjusted=preload_depth < plan.preload_depth,
            min_required_records=plan.min_required_records,
            probe=None,
        )
        refined = cls._attach_memory_budgets(base, probe_result)
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
        base_plan = cls._resolve_base_plan(jobs, capacity, probe_result, performance)
        final_plan = cls._attach_memory_budgets(base_plan, probe_result)

        # 始终挂 probe 快照：真探针或规划默认单价（报告可回填 estimated）
        probe_snap = cls._probe_to_dict(probe_result)
        if probe_snap is None:
            probe_snap = {
                "ran": False,
                "source": "plan_defaults",
                "slices_sampled": 0,
                "mb_per_slice_reader": _DEFAULT_MB_PER_SLICE_READER,
                "mb_per_slice_compute": _DEFAULT_MB_PER_SLICE_COMPUTE,
                "mb_per_slice_payload": _DEFAULT_MB_PER_SLICE_PAYLOAD,
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
        """Apply already-resolved width / R / N from performance into a plan."""
        slice_open_days = int(
            performance.get(
                "slice_open_days", SliceMemoryPlanner.DEFAULT_MIN_REQUIRED
            )
        )
        total_slices = cls._count_calendar_slices(jobs, slice_open_days)
        # R may be 0 on single-core hosts.
        reader_workers = max(0, int(performance.get("reader_workers", 0)))
        compute_processes = int(
            performance.get(
                "compute_processes", SliceMemoryPlanner.COMPUTE_PROCESSES
            )
        )
        prefetch_enabled = bool(performance.get("prefetch_enabled", True))

        mb_reader = (
            probe_result.mb_per_slice_reader
            if probe_result
            else _DEFAULT_MB_PER_SLICE_READER
        )
        mb_payload = (
            probe_result.mb_per_slice_payload
            if probe_result
            else _DEFAULT_MB_PER_SLICE_PAYLOAD
        )
        mb_compute = (
            probe_result.mb_per_slice_compute
            if probe_result
            else _DEFAULT_MB_PER_SLICE_COMPUTE
        )

        raw_depth = performance.get("preload_depth")
        if raw_depth in (None, "", "auto"):
            preload_depth = _DEFAULT_PRELOAD_DEPTH if prefetch_enabled else 0
        else:
            preload_depth = max(0, int(raw_depth))
            if not prefetch_enabled:
                preload_depth = 0

        return SliceDispatchPlan(
            reader_workers=reader_workers,
            reader_memory_budget_mb=0.0,  # filled in attach pass
            compute_processes=compute_processes,
            compute_memory_budget_mb=mb_compute,
            queue_capacity=preload_depth,
            preload_depth=preload_depth,
            slice_open_days=slice_open_days,
            dispatch_jobs=max(1, total_slices),
            memory_budget_mb=capacity.memory_budget_mb,
            oom_adjusted=False,
            min_required_records=SliceMemoryPlanner.default_min_required(
                performance.get("min_required_records")
            ),
        )

    @classmethod
    def _attach_memory_budgets(
        cls,
        base_plan: SliceDispatchPlan,
        probe_result: Optional[SliceProbeResult],
    ) -> SliceDispatchPlan:
        """Fill reader/compute budgets from depth × unit MB (queue already sized)."""
        mb_reader = (
            probe_result.mb_per_slice_reader
            if probe_result
            else _DEFAULT_MB_PER_SLICE_READER
        )
        mb_compute = (
            probe_result.mb_per_slice_compute
            if probe_result
            else _DEFAULT_MB_PER_SLICE_COMPUTE
        )
        depth = base_plan.preload_depth
        return SliceDispatchPlan(
            reader_workers=base_plan.reader_workers,
            reader_memory_budget_mb=depth * mb_reader,
            compute_processes=base_plan.compute_processes,
            compute_memory_budget_mb=mb_compute,
            queue_capacity=depth,
            preload_depth=depth,
            slice_open_days=base_plan.slice_open_days,
            dispatch_jobs=base_plan.dispatch_jobs,
            memory_budget_mb=base_plan.memory_budget_mb,
            oom_adjusted=base_plan.oom_adjusted,
            min_required_records=base_plan.min_required_records,
            probe=base_plan.probe,
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