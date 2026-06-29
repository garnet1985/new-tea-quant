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

logger = logging.getLogger(__name__)


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
    ) -> Tuple[DispatchPlan, List[JobBatch]]:
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
        
        # Step 5: build_monitor (TODO: 未来实现动态planner)
        # monitor = TimelinePlanner._build_monitor(plan, performance)
        
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
        
        return plan, batches
    
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
        """
        Step 3: 根据探针结果制定规划（2步流程）。
        
        流程：
        1. 计算基础规划（worker + bundle size）
        2. OOM保护（基于内存预算调整）
        
        Args:
            jobs: 待执行的job列表
            capacity: 机器容量
            probe_result: 探针结果
            performance: 配置字典
            log_label: 日志标签
            
        Returns:
            DispatchPlan: 调度规划结果
        """
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
        
        # Step 1: 计算基础规划（worker + bundle size）
        entities_per_job, max_workers = TimelinePlanner._resolve_base_plan(
            total_entities, capacity, probe_result, performance
        )
        
        # Step 2: OOM保护（基于内存预算调整）
        entities_per_job, max_workers, oom_adjusted = TimelinePlanner._apply_oom_protection(
            entities_per_job, max_workers, capacity, probe_result, performance, log_label
        )
        
        # 计算dispatch_jobs和worker_job_budget
        dispatch_jobs = max(1, math.ceil(total_entities / entities_per_job))
        worker_job_budget_mb = entities_per_job * probe_result.mb_per_entity
        
        # 构建source标记
        epj_source = "oom_adjusted" if oom_adjusted else "base_plan"
        mw_source = "oom_adjusted" if oom_adjusted else "base_plan"
        
        return DispatchPlan(
            entities_per_job=entities_per_job,
            max_workers=max_workers,
            dispatch_jobs=dispatch_jobs,
            prefetch_ahead=1,
            memory_budget_mb=capacity.memory_budget_mb,
            worker_job_budget_mb=worker_job_budget_mb,
            source_entities_per_job=epj_source,
            source_max_workers=mw_source,
        )
    
    @staticmethod
    def _resolve_base_plan(
        total_entities: int,
        capacity: MachineCapacity,
        probe_result: ProbeResult,
        performance: Dict[str, Any],
    ) -> Tuple[int, int]:
        """计算基础规划（worker + bundle size，不考虑内存）。
        
        Args:
            total_entities: 总entity数量
            capacity: 机器容量
            probe_result: 探针结果
            performance: 配置字典
            
        Returns:
            Tuple[int, int]: (entities_per_job, max_workers)
        """
        # 计算entities_per_job（实验数据驱动）
        entities_per_job = TimelinePlanner._resolve_entities_per_job_base(
            total_entities, performance
        )
        
        # 计算max_workers（实验数据驱动）
        max_workers = TimelinePlanner._resolve_max_workers_base(
            total_entities, capacity, performance
        )
        
        return entities_per_job, max_workers
    
    @staticmethod
    def _resolve_entities_per_job_base(
        total_entities: int,
        performance: Dict[str, Any],
    ) -> int:
        """计算基础entities_per_job（实验数据驱动，不考虑内存）。
        
        Args:
            total_entities: 总entity数量
            performance: 配置字典
            
        Returns:
            int: entities_per_job
        """
        epj_override = performance.get("entities_per_job")
        
        if epj_override not in (None, "", "auto"):
            # 用户指定值，应用clamp约束
            epj = max(1, int(epj_override))
            return TimelinePlanner._clamp_entities(epj, performance)
        
        # 实验数据驱动的启发式规则
        if total_entities < 200:
            return 5
        elif total_entities < 1000:
            return 10
        else:
            return 5
    
    @staticmethod
    def _resolve_max_workers_base(
        total_entities: int,
        capacity: MachineCapacity,
        performance: Dict[str, Any],
    ) -> int:
        """计算基础max_workers（实验数据驱动，不考虑内存）。
        
        Args:
            total_entities: 总entity数量
            capacity: 机器容量
            performance: 配置字典
            
        Returns:
            int: max_workers
        """
        mw_override = performance.get("max_workers")
        
        if mw_override not in (None, "", "auto"):
            # 用户指定值
            return max(1, int(mw_override))
        
        # 实验数据驱动的启发式规则
        available_workers = MachineInfo.get_available_workers(capacity)
        
        if total_entities < 200:
            return 1
        elif total_entities < 1000:
            return min(2, available_workers)
        else:
            return min(4, available_workers)
    
    @staticmethod
    def _apply_oom_protection(
        entities_per_job: int,
        max_workers: int,
        capacity: MachineCapacity,
        probe_result: ProbeResult,
        performance: Dict[str, Any],
        log_label: str,
    ) -> Tuple[int, int, bool]:
        """OOM保护（基于内存预算调整worker和bundle size）。
        
        Args:
            entities_per_job: 基础entities_per_job
            max_workers: 基础max_workers
            capacity: 机器容量
            probe_result: 探针结果
            performance: 配置字典
            log_label: 日志标签
            
        Returns:
            Tuple[int, int, bool]: (adjusted_entities_per_job, adjusted_max_workers, oom_adjusted)
        """
        # 计算当前内存使用
        worker_job_budget_mb = entities_per_job * probe_result.mb_per_entity
        total_memory_usage_mb = worker_job_budget_mb * max_workers
        
        # 可用内存预算（减去底线）
        available_memory_mb = capacity.memory_budget_mb - capacity.memory_floor_mb
        
        # 检查是否OOM
        if total_memory_usage_mb <= available_memory_mb:
            # 没有OOM风险，保持原值
            return entities_per_job, max_workers, False
        
        # OOM风险，需要调整
        logger.warning(
            "%sOOM风险检测: 当前使用=%.1fMB, 可用=%.1fMB, 调整规划...",
            log_label,
            total_memory_usage_mb,
            available_memory_mb,
        )
        
        # 调整策略：优先降低max_workers，再降低entities_per_job
        # Step 1: 尝试降低max_workers
        max_workers_by_memory = int(available_memory_mb / worker_job_budget_mb)
        if max_workers_by_memory >= 1:
            # 降低max_workers足够
            adjusted_max_workers = max(1, max_workers_by_memory)
            logger.info(
                "%sOOM保护: max_workers %s → %s (内存约束)",
                log_label,
                max_workers,
                adjusted_max_workers,
            )
            return entities_per_job, adjusted_max_workers, True
        
        # Step 2: 需要同时降低entities_per_job和max_workers
        # 计算最小可行的entities_per_job（至少1个entity）
        max_entities_by_memory = int(available_memory_mb / probe_result.mb_per_entity)
        adjusted_entities_per_job = max(1, min(entities_per_job, max_entities_by_memory))
        
        # 重新计算max_workers
        adjusted_worker_job_budget_mb = adjusted_entities_per_job * probe_result.mb_per_entity
        adjusted_max_workers = max(1, int(available_memory_mb / adjusted_worker_job_budget_mb))
        
        logger.info(
            "%sOOM保护: entities_per_job %s → %s, max_workers %s → %s (内存约束)",
            log_label,
            entities_per_job,
            adjusted_entities_per_job,
            max_workers,
            adjusted_max_workers,
        )
        
        return adjusted_entities_per_job, adjusted_max_workers, True
    
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
    ) -> Optional[Any]:
        """
        Step 5: 制定一个动态planner，定期进行重新plan。
        
        TODO: 未来实现动态规划
        - 监控执行进度
        - 定期重新规划（调整并发度）
        - 动态调整entities_per_job
        """
        # 简化：当前不实现动态planner
        return None


__all__ = [
    "DispatchPlan",
    "JobBatch",
    "TimelinePlanner",
]