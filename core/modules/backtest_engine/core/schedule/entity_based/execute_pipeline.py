"""entity_based execute pipeline: plan → monitor → process-pool execution."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from core.modules.backtest_engine.core.shared.context import ExecutionContext
from core.infra.machine_capacity import MachineInfo
from core.modules.backtest_engine.core.shared.modes import BacktestMode
from core.modules.backtest_engine.core.shared.progress import RunPhase, RunProgressReporter
from core.modules.backtest_engine.core.shared.types import (
    TaskStartFn,
    TaskCompleteFn,
    JobReport,
    RunProgress,
)
from core.modules.backtest_engine.core.schedule.entity_based.executor import EntityExecutor
from core.modules.backtest_engine.core.schedule.entity_based.executor_duckdb import (
    EntityExecutorDuckDB,
)
from core.modules.backtest_engine.core.schedule.entity_based.monitor import (
    MonitorPlanSnapshot,
    EntityJobSample,
    EntityMonitorConfig,
    EntityRunMonitor,
)
from core.modules.backtest_engine.core.shared.jobs import BacktestJob
from core.modules.backtest_engine.core.schedule.entity_based.planner import (
    DispatchPlan,
    JobBatch,
    EntityPlanner,
)

logger = logging.getLogger(__name__)


class EntityExecutePipeline:
    """End-to-end entity_based backtest: plan → monitor → execute."""

    ExecuteFn = EntityExecutor.ExecuteFn
    OnTaskResultHook = EntityExecutor.OnTaskResultHook
    OnAfterAllTasksCompleteHook = EntityExecutor.OnAfterAllTasksCompleteHook

    @dataclass(frozen=True)
    class Result:
        plan: DispatchPlan
        batches: List[JobBatch]
        monitor_config: EntityMonitorConfig
        execution: EntityExecutor.ExecutionResult
        monitor_stats: Any = None
        pipeline_phases_sec: Optional[Dict[str, float]] = None

    def __init__(self, *, log_label: str = "entity_based") -> None:
        self._log_label = log_label

    def run(
        self,
        jobs: List[Dict[str, Any]],
        performance: Dict[str, Any],
        *,
        execute_fn: EntityExecutor.ExecuteFn,
        task_name: str = "",
        on_before_all_tasks_start: Optional[Callable[[Any, List[Any]], None]] = None,
        on_before_task_start: Optional[TaskStartFn] = None,
        on_after_task_complete: Optional[TaskCompleteFn] = None,
        on_after_all_tasks_complete: Optional[Callable[[List[JobReport]], None]] = None,
        on_task_result: Optional[Callable[[JobReport, RunProgress], None]] = None,
        enable_progress_display: bool = True,
    ) -> EntityExecutePipeline.Result:
        label = task_name or self._log_label
        wall_t0 = time.perf_counter()
        phase_marks: Dict[str, float] = {"prep": wall_t0}
        progress = RunProgressReporter(
            task_name=label,
            run_mode=BacktestMode.ENTITY_BASED.value,
            enable_progress_display=enable_progress_display,
        )
        progress.mark_phase(RunPhase.PREP)

        if jobs:
            BacktestJob.validate_many(jobs, mode=BacktestMode.ENTITY_BASED)

        phase_marks["plan"] = time.perf_counter()
        progress.mark_phase(RunPhase.PLAN)
        plan, batches, monitor_config = self._plan(
            jobs,
            performance,
            execute_fn,
            on_before_task_start=on_before_task_start,
            on_after_task_complete=on_after_task_complete,
        )
        progress.set_execute_total(len(batches))

        # 全局初始化钩子（有了plan以后，准备执行前）
        # 用于查看/修改plan
        if on_before_all_tasks_start is not None:
            try:
                on_before_all_tasks_start(plan, batches)
            except Exception as e:
                logger.warning(f"on_before_all_tasks_start failed: {e}")

        capacity = MachineInfo.get_capacity(performance)
        available_memory_mb = MachineInfo.worker_pool_budget_mb(capacity)
        monitor = EntityRunMonitor(
            MonitorPlanSnapshot(
                entities_per_job=plan.entities_per_job,
                max_workers=plan.max_workers,
                prefetch_ahead=plan.prefetch_ahead,
                worker_job_budget_mb=plan.worker_job_budget_mb,
            ),
            monitor_config,
            available_memory_mb=available_memory_mb,
            cpu_workers_cap=MachineInfo.get_available_workers(capacity),
        )
        
        context = ExecutionContext.create(
            task_name=label,
            total_jobs=len(batches),
            executor="",
            performance=performance,
        )

        batch_entities = {batch.batch_id: batch.entities_count for batch in batches}

        def monitored_on_task_result(report: JobReport, run_progress: RunProgress) -> None:
            monitor.record(
                _job_sample_from_report(report, batch_entities),
            )
            progress.mark_execute_unit(run_progress.finished)
            if on_task_result is not None:
                on_task_result(report, run_progress)

        phase_marks["execute"] = time.perf_counter()
        progress.mark_phase(RunPhase.EXECUTE)
        execution = EntityExecutorDuckDB.execute(
            plan,
            batches,
            context,
            execute_fn,
            on_task_result=monitored_on_task_result,
            on_after_all_tasks_complete=on_after_all_tasks_complete,
            on_before_task_start=on_before_task_start,
            on_after_task_complete=on_after_task_complete,
            log_label=self._log_label,
            get_admission_limit=lambda: monitor.admission_limit,
            duckdb_process_pool_scope=str(
                performance.get("duckdb_process_pool_scope", "auto")
            ),
            duckdb_resume_main_after_pool=bool(
                performance.get("duckdb_resume_main_after_pool", True)
            ),
        )
        monitor.flush()
        phase_marks["finish"] = time.perf_counter()
        progress.mark_phase(RunPhase.FINISH)
        wall_end = time.perf_counter()

        return EntityExecutePipeline.Result(
            plan=plan,
            batches=batches,
            monitor_config=monitor_config,
            execution=execution,
            monitor_stats=monitor.stats,
            pipeline_phases_sec=_pipeline_phases_sec(phase_marks, wall_end),
        )

    def _plan(
        self,
        jobs: List[Dict[str, Any]],
        performance: Dict[str, Any],
        execute_fn: EntityExecutor.ExecuteFn,
        *,
        on_before_task_start: Optional[TaskStartFn] = None,
        on_after_task_complete: Optional[TaskCompleteFn] = None,
    ) -> tuple[DispatchPlan, List[JobBatch], EntityMonitorConfig]:
        return EntityPlanner.plan_jobs(
            jobs,
            performance,
            execute_fn=execute_fn,
            on_before_task_start=on_before_task_start,
            on_after_task_complete=on_after_task_complete,
            log_label=self._log_label,
        )


def _pipeline_phases_sec(phase_marks: Dict[str, float], wall_end: float) -> Dict[str, float]:
    """Convert phase start marks → per-phase + total wall seconds."""
    prep_t0 = float(phase_marks.get("prep") or wall_end)
    plan_t0 = float(phase_marks.get("plan") or prep_t0)
    execute_t0 = float(phase_marks.get("execute") or plan_t0)
    finish_t0 = float(phase_marks.get("finish") or execute_t0)
    return {
        "prep": round(max(0.0, plan_t0 - prep_t0), 4),
        "plan": round(max(0.0, execute_t0 - plan_t0), 4),
        "execute": round(max(0.0, finish_t0 - execute_t0), 4),
        "finish": round(max(0.0, wall_end - finish_t0), 4),
        "wall": round(max(0.0, wall_end - prep_t0), 4),
    }


def _job_sample_from_report(
    report: JobReport,
    batch_entities: Dict[str, int],
) -> EntityJobSample:
    data = report.data if isinstance(report.data, dict) else {}
    entities_count = int(
        data.get("entities_count") or batch_entities.get(report.job_id, 0)
    )
    engine = data.get("engine_perf") or {}
    peak_rss = data.get("peak_rss_mb")
    if peak_rss is None and isinstance(engine, dict):
        peak_rss = engine.get("peak_rss_mb")
    wall_sec = float(data.get("wall_sec") or (engine.get("wall_sec") if isinstance(engine, dict) else 0) or 0.0)
    return EntityJobSample(
        job_id=report.job_id,
        entities_count=entities_count,
        wall_sec=wall_sec,
        peak_rss_mb=float(peak_rss) if peak_rss is not None else None,
        success=report.success,
    )


__all__ = ["EntityExecutePipeline"]
