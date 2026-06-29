"""
Backtest Engine - Timeline-based Planner

时间线模式的调度规划器：5步骤显式流程。

职责（执行前的规划动作）：
- Step 1: get_machine_capacity    # 得到CPU和内存预算
- Step 2: dispatch_probe          # 小批次探针测量
- Step 3: settle_plan             # 根据探针结果制定规划
- Step 4: split_job_batches       # 切割jobs
- Step 5: build_monitor           # 动态planner（TODO）

特点：
- 显式5步骤流程（清晰易维护）
- timeline和slice共享流程框架（内部实现不同）
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from core.modules.backtest_engine.core.shared.machine_info import (
    MachineInfo,
    MachineCapacity,
)
from core.modules.backtest_engine.core.timeline_based.probe import (
    Probe,
    ProbeResult,
)
from core.modules.backtest_engine.core.timeline_based.monitor import (
    MonitorPlanSnapshot,
    TimelineMonitorConfig,
)

logger = logging.getLogger(__name__)

# stock_based v1 (2026-06-22): epj=5 optimal wall time vs epj=1; see devtools/performance/strategy/enumerator/reports/v1/
DEFAULT_OPTIMAL_ENTITIES_PER_JOB: int = 5
DEFAULT_PREFETCH_AHEAD: int = 1


@dataclass(frozen=True)
class DispatchPlan:
    """调度规划（Step 3结果）。"""
    
    entities_per_job: int
    max_workers: int
    dispatch_jobs: int
    prefetch_ahead: int
    memory_budget_mb: float
    worker_job_budget_mb: float
    source_entities_per_job: str
    source_max_workers: str


@dataclass(frozen=True)
class JobBatch:
    """切割后的job批次（Step 4结果）。"""
    
    batch_id: str
    entity_ids: List[str]
    entities_count: int
    payload: Dict[str, Any]


class TimelinePlanner:
    """
    Timeline模式调度规划器（面向对象方式）。
    
    5步骤显式流程：
    - Step 1: get_machine_capacity    # 得到CPU和内存预算
    - Step 2: dispatch_probe          # 小批次探针测量
    - Step 3: settle_plan             # 根据探针结果制定规划
    - Step 4: split_job_batches       # 切割jobs
    - Step 5: build_monitor           # 动态planner（TODO）
    """
    
    @staticmethod
    def plan_jobs(
        jobs: List[Dict[str, Any]],
        performance: Dict[str, Any],
        executor: Optional[str] = None,
        log_label: str = "调度",
    ) -> Tuple[DispatchPlan, List[JobBatch], TimelineMonitorConfig]:
        """
        Planner的编排层（对外API）。
        
        完整的5步骤流程：
        1. get_machine_capacity: 得到当前电脑配置
        2. dispatch_probe: 对jobs进行小切割探针测量
        3. settle_plan: 根据探针结果制定规划
        4. split_job_batches: 根据plan切割jobs
        5. build_monitor: 制定动态planner
        
        Args:
            jobs: 待执行的job列表
            performance: 配置字典
            executor: 执行器标识字符串（"tag", "strategy.enum", "strategy.price"）
            log_label: 日志标签
            
        Returns:
            (DispatchPlan, List[JobBatch]): 规划结果和切割后的job批次
        """
        # Step 1: get_machine_capacity
        capacity = TimelinePlanner._get_machine_capacity(performance)
        
        # Step 2: dispatch_probe
        probe_result = TimelinePlanner._dispatch_probe(
            jobs, capacity, performance, executor, log_label
        )
        
        # Step 3: settle_plan
        plan = TimelinePlanner._settle_plan(
            jobs, capacity, probe_result, performance, log_label
        )
        
        # Step 4: split_job_batches
        batches = TimelinePlanner._split_job_batches(jobs, plan)
        
        # Step 5: build_monitor
        monitor_config = TimelinePlanner._build_monitor(plan, performance)
        
        logger.info(
            "%s规划完成: capacity(cpu=%s, mem=%.1fMB), "
            "probe(mb=%.1fMB/entity), plan(epj=%s, workers=%s, jobs=%s), batches=%s",
            log_label,
            capacity.cpu_count,
            capacity.memory_budget_mb,
            probe_result.mb_per_entity,
            plan.entities_per_job,
            plan.max_workers,
            plan.dispatch_jobs,
            len(batches),
        )
        
        return plan, batches, monitor_config
    
    # ===== Step 1: get_machine_capacity =====
    
    @staticmethod
    def _get_machine_capacity(performance: Dict[str, Any]) -> MachineCapacity:
        """
        Step 1: 得到当前电脑配置，CPU和内存预算。
        
        Args:
            performance: 配置字典
            
        Returns:
            MachineCapacity: 机器容量结果
        """
        return MachineInfo.get_capacity(performance)
    
    # ===== Step 2: dispatch_probe =====
    
    @staticmethod
    def _dispatch_probe(
        jobs: List[Dict[str, Any]],
        capacity: MachineCapacity,
        performance: Dict[str, Any],
        executor: Optional[str],
        log_label: str,
    ) -> ProbeResult:
        """
        Step 2: 对jobs进行小切割，变成一个小批次放入探针，得到结果。
        
        Args:
            jobs: 待执行的job列表
            capacity: 机器容量
            performance: 配置字典
            executor: 执行器标识字符串（用于probe执行）
            log_label: 日志标签
            
        Returns:
            ProbeResult: 探针结果
        """
        total_entities = len(jobs)
        
        # 判断是否需要运行探针
        should_probe = Probe.should_run(performance, total_entities)
        
        if not should_probe:
            # 不运行探针，使用默认值
            return Probe._get_default_result(performance)
        
        # 确定探针entity数量
        probe_entities_count = TimelinePlanner._get_probe_entities_count(
            total_entities, capacity
        )
        
        # 构建探针jobs
        probe_jobs = Probe.build_probe_jobs(jobs, probe_entities_count)
        
        # 执行探针
        logger.info(
            "%s探针启动: entities=%s, probe_entities=%s, executor=%s",
            log_label,
            total_entities,
            probe_entities_count,
            executor or "default",
        )
        
        return Probe.dispatch(probe_jobs, executor or "default", performance, log_label)
    
    @staticmethod
    def _get_probe_entities_count(total_entities: int, capacity: MachineCapacity) -> int:
        """确定探针entity数量。"""
        # 默认探针数量：20个entity
        default_probe_count = 20
        
        # 约束：不超过总entity数，不超过内存预算
        max_by_memory = int(capacity.memory_budget_mb / 10.0)  # 假设每entity 10MB
        
        return min(
            default_probe_count,
            total_entities,
            max_by_memory,
        )
    
    # ===== Step 3: settle_plan =====
    
    @staticmethod
    def _settle_plan(
        jobs: List[Dict[str, Any]],
        capacity: MachineCapacity,
        probe_result: ProbeResult,
        performance: Dict[str, Any],
        log_label: str,
    ) -> DispatchPlan:
        """Step 3: optimal epj/workers first, then cap by memory budget."""
        total_entities = len(jobs)

        if total_entities <= 0:
            return DispatchPlan(
                entities_per_job=1,
                max_workers=1,
                dispatch_jobs=0,
                prefetch_ahead=0,
                memory_budget_mb=capacity.memory_budget_mb,
                worker_job_budget_mb=0.0,
                source_entities_per_job="empty",
                source_max_workers="empty",
            )

        mb_per_entity = TimelinePlanner._resolve_mb_per_entity(
            probe_result,
            performance,
            log_label,
        )
        available_memory_mb = max(
            1.0,
            capacity.memory_budget_mb - capacity.memory_floor_mb,
        )

        entities_per_job, epj_source = TimelinePlanner._resolve_entities_per_job(
            total_entities=total_entities,
            mb_per_entity=mb_per_entity,
            memory_budget_mb=capacity.memory_budget_mb,
            performance=performance,
            log_label=log_label,
        )
        worker_job_budget_mb = max(1.0, entities_per_job * mb_per_entity)

        max_workers, mw_source = TimelinePlanner._resolve_max_workers(
            total_entities=total_entities,
            entities_per_job=entities_per_job,
            worker_job_budget_mb=worker_job_budget_mb,
            available_memory_mb=available_memory_mb,
            capacity=capacity,
            performance=performance,
            log_label=log_label,
        )

        dispatch_jobs = max(1, math.ceil(total_entities / entities_per_job))
        prefetch_raw = performance.get("prefetch_ahead")
        prefetch_ahead = (
            DEFAULT_PREFETCH_AHEAD
            if prefetch_raw is None
            else max(0, int(prefetch_raw))
        )

        logger.info(
            "%s规划: entities=%s → jobs≈%s (epj=%s, %s, job≈%.1fMB), "
            "workers=%s (%s), prefetch=%s, budget=%.0fMB (avail≈%.0fMB), "
            "mb/entity=%.3f",
            log_label,
            total_entities,
            dispatch_jobs,
            entities_per_job,
            epj_source,
            worker_job_budget_mb,
            max_workers,
            mw_source,
            prefetch_ahead,
            capacity.memory_budget_mb,
            available_memory_mb,
            mb_per_entity,
        )

        return DispatchPlan(
            entities_per_job=entities_per_job,
            max_workers=max_workers,
            dispatch_jobs=dispatch_jobs,
            prefetch_ahead=prefetch_ahead,
            memory_budget_mb=capacity.memory_budget_mb,
            worker_job_budget_mb=worker_job_budget_mb,
            source_entities_per_job=epj_source,
            source_max_workers=mw_source,
        )

    @staticmethod
    def _resolve_mb_per_entity(
        probe_result: ProbeResult,
        performance: Dict[str, Any],
        log_label: str,
    ) -> float:
        staged = performance.get("mb_per_entity_staged")
        if staged not in (None, ""):
            return max(0.01, float(staged))
        if probe_result.entities_sampled > 0:
            return max(0.01, float(probe_result.mb_per_entity))
        epj_override = performance.get("entities_per_job")
        if epj_override not in (None, "", "auto"):
            return 1.0
        raise ValueError(
            f"{log_label}: entities_per_job=auto 需要调度探针或 mb_per_entity_staged"
        )

    @staticmethod
    def _recommended_entities_per_job(
        total_entities: int,
        performance: Dict[str, Any],
    ) -> int:
        """Experiment-backed optimal epj (stock_based v1, 2026-06-22)."""
        if total_entities < 200:
            recommended = DEFAULT_OPTIMAL_ENTITIES_PER_JOB
        elif total_entities < 1000:
            recommended = 10
        else:
            recommended = DEFAULT_OPTIMAL_ENTITIES_PER_JOB
        return TimelinePlanner._clamp_entities(recommended, performance)

    @staticmethod
    def _recommended_max_workers(
        total_entities: int,
        capacity: MachineCapacity,
    ) -> int:
        """Experiment-backed optimal worker count by scale."""
        cpu_cap = MachineInfo.get_available_workers(capacity)
        if total_entities < 200:
            return 1
        if total_entities < 1000:
            return min(2, cpu_cap)
        return min(4, cpu_cap)

    @staticmethod
    def _resolve_entities_per_job(
        *,
        total_entities: int,
        mb_per_entity: float,
        memory_budget_mb: float,
        performance: Dict[str, Any],
        log_label: str,
    ) -> Tuple[int, str]:
        epj_override = performance.get("entities_per_job")
        if epj_override not in (None, "", "auto"):
            epj = TimelinePlanner._clamp_entities(max(1, int(epj_override)), performance)
            return epj, "settings"

        optimal_epj = TimelinePlanner._recommended_entities_per_job(
            total_entities, performance
        )
        single_job_mb = optimal_epj * mb_per_entity
        if single_job_mb <= memory_budget_mb:
            return optimal_epj, "optimal"

        max_epj = max(1, int(memory_budget_mb / mb_per_entity))
        epj_min = max(1, int(performance.get("entities_per_job_min", 1)))
        fitted = max(epj_min, min(optimal_epj, max_epj))
        fitted = TimelinePlanner._clamp_entities(fitted, performance)
        logger.info(
            "%s单 job 内存 %.1fMB 超过 budget %.0fMB，epj %s → %s",
            log_label,
            single_job_mb,
            memory_budget_mb,
            optimal_epj,
            fitted,
        )
        return fitted, "memory_capped"

    @staticmethod
    def _resolve_max_workers(
        *,
        total_entities: int,
        entities_per_job: int,
        worker_job_budget_mb: float,
        available_memory_mb: float,
        capacity: MachineCapacity,
        performance: Dict[str, Any],
        log_label: str,
    ) -> Tuple[int, str]:
        mw_override = performance.get("max_workers")
        if mw_override not in (None, "", "auto"):
            return max(1, int(mw_override)), "settings"

        dispatch_jobs = (
            max(1, math.ceil(total_entities / entities_per_job))
            if total_entities > 0
            else None
        )
        cpu_workers = MachineInfo.resolve_max_workers(
            performance,
            dispatch_jobs=dispatch_jobs,
        )
        optimal_workers = TimelinePlanner._recommended_max_workers(
            total_entities, capacity
        )
        max_workers = max(1, min(optimal_workers, cpu_workers))
        source = "optimal+auto_cpu"

        total_in_flight_mb = worker_job_budget_mb * max_workers
        if total_in_flight_mb <= available_memory_mb:
            return max_workers, source

        capped = max(1, int(available_memory_mb / worker_job_budget_mb))
        capped = min(max_workers, capped)
        logger.info(
            "%s并发内存 %.1fMB 超过可用 %.0fMB，workers %s → %s",
            log_label,
            total_in_flight_mb,
            available_memory_mb,
            max_workers,
            capped,
        )
        return capped, "memory_capped"
    
    @staticmethod
    def _clamp_entities(n: int, performance: Dict[str, Any]) -> int:
        """约束entities_per_job到合理范围。"""
        lo = max(5, int(performance.get("entities_per_job_min", 5)))
        hi = max(lo, min(50, int(performance.get("entities_per_job_max", 50))))
        return max(lo, min(hi, n))
    
    # ===== Step 4: split_job_batches =====
    
    @staticmethod
    def _split_job_batches(
        jobs: List[Dict[str, Any]],
        plan: DispatchPlan,
    ) -> List[JobBatch]:
        """
        Step 4: 根据plan切割jobs。
        
        Args:
            jobs: 待执行的job列表
            plan: 调度规划
            
        Returns:
            List[JobBatch]: 切割后的job批次列表
        """
        if plan.dispatch_jobs <= 0:
            return []
        
        batches = []
        entities_per_job = plan.entities_per_job
        
        for i in range(plan.dispatch_jobs):
            start_idx = i * entities_per_job
            end_idx = min(start_idx + entities_per_job, len(jobs))
            
            batch_entities = jobs[start_idx:end_idx]
            
            batch = JobBatch(
                batch_id=f"batch_{i}",
                entity_ids=[job.get("entity_id", "") for job in batch_entities],
                entities_count=len(batch_entities),
                payload={"jobs": batch_entities},
            )
            
            batches.append(batch)
        
        return batches
    
    # ===== Step 5: build_monitor (TODO) =====
    
    @staticmethod
    def _build_monitor(
        plan: DispatchPlan,
        performance: Dict[str, Any],
    ) -> TimelineMonitorConfig:
        """Step 5: monitor evaluation window config (runtime adjust in-flight only)."""
        snapshot = MonitorPlanSnapshot(
            entities_per_job=plan.entities_per_job,
            max_workers=plan.max_workers,
            prefetch_ahead=plan.prefetch_ahead,
            worker_job_budget_mb=plan.worker_job_budget_mb,
        )
        return TimelineMonitorConfig.from_dispatch_plan(snapshot, performance)


__all__ = [
    "DispatchPlan",
    "JobBatch",
    "TimelinePlanner",
]