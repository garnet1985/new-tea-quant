"""entity_based execute pipeline: plan → monitor → process-pool execution."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.modules.backtest_engine.core.shared.context import ExecutionContext
from core.infra.machine_capacity import MachineInfo
from core.modules.backtest_engine.core.shared.modes import BacktestMode
from core.modules.backtest_engine.core.shared.progress import RunPhase, RunProgressReporter
from core.modules.backtest_engine.core.shared.types import (
    ChildProcessTaskStartFn,
    ChildProcessTaskCompleteFn,
    JobReport,
    RunProgress,
)
from core.modules.backtest_engine.core.entity_based.executor import EntityExecutor
from core.modules.backtest_engine.core.entity_based.executor_duckdb import (
    EntityExecutorDuckDB,
)
from core.modules.backtest_engine.core.entity_based.monitor import (
    MonitorPlanSnapshot,
    EntityJobSample,
    EntityMonitorConfig,
    EntityRunMonitor,
)
from core.modules.backtest_engine.core.shared.jobs import BacktestJob
from core.modules.backtest_engine.core.entity_based.planner import (
    DispatchPlan,
    JobBatch,
    EntityPlanner,
)

logger = logging.getLogger(__name__)


class EntityExecutePipeline:
    """End-to-end entity_based backtest: plan → monitor → execute."""

    ExecuteFn = EntityExecutor.ExecuteFn
    OnSingleTaskResultHook = EntityExecutor.OnSingleTaskResultHook
    OnAfterAllTasksCompleteHook = EntityExecutor.OnAfterAllTasksCompleteHook

    @dataclass(frozen=True)
    class Result:
        plan: DispatchPlan
        batches: List[JobBatch]
        monitor_config: EntityMonitorConfig
        execution: EntityExecutor.ExecutionResult
        monitor_stats: Any = None

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
        on_child_process_task_start: Optional[ChildProcessTaskStartFn] = None,
        on_child_process_task_complete: Optional[ChildProcessTaskCompleteFn] = None,
        on_after_all_tasks_complete: Optional[Callable[[List[JobReport]], None]] = None,
        enable_progress_display: bool = True,
    ) -> EntityExecutePipeline.Result:
        label = task_name or self._log_label
        progress = RunProgressReporter(
            task_name=label,
            run_mode=BacktestMode.ENTITY_BASED.value,
            enable_progress_display=enable_progress_display,
        )
        progress.mark_phase(RunPhase.PREP)

        if jobs:
            BacktestJob.validate_many(jobs, mode=BacktestMode.ENTITY_BASED)

        progress.mark_phase(RunPhase.PLAN)
        plan, batches, monitor_config = self._plan(
            jobs,
            performance,
            execute_fn,
            on_child_process_task_start=on_child_process_task_start,
            on_child_process_task_complete=on_child_process_task_complete,
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

        def monitored_on_single_task_result(report: JobReport, run_progress: RunProgress) -> None:
            monitor.record(
                _job_sample_from_report(report, batch_entities),
            )
            progress.mark_execute_unit(run_progress.finished)
            if on_result is not None:
                on_result(report, run_progress)

                # 全局初始化钩子
        if on_all_jobs_start is not None:
            try:
                on_all_jobs_start()
            except Exception as e:
                logger.warning(f"on_all_jobs_start failed: {e}")

        progress.mark_phase(RunPhase.EXECUTE)
        execution = EntityExecutorDuckDB.execute(
            plan,
            batches,
            context,
            execute_fn,
            on_single_task_result=monitored_on_single_task_result,
            on_after_all_tasks_complete=on_after_all_tasks_complete,
            on_child_process_task_start=on_child_process_task_start,
            on_child_process_task_complete=on_child_process_task_complete,
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
        progress.mark_phase(RunPhase.FINISH)

        return EntityExecutePipeline.Result(
            plan=plan,
            batches=batches,
            monitor_config=monitor_config,
            execution=execution,
            monitor_stats=monitor.stats,
        )

    def _plan(
        self,
        jobs: List[Dict[str, Any]],
        performance: Dict[str, Any],
        execute_fn: EntityExecutor.ExecuteFn,
        *,
        on_child_process_task_start: Optional[ChildProcessTaskStartFn] = None,
        on_child_process_task_complete: Optional[ChildProcessTaskCompleteFn] = None,
    ) -> tuple[DispatchPlan, List[JobBatch], EntityMonitorConfig]:
        return EntityPlanner.plan_jobs(
            jobs,
            performance,
            execute_fn=execute_fn,
            on_child_process_task_start=on_child_process_task_start,
            on_child_process_task_complete=on_child_process_task_complete,
            log_label=self._log_label,
        )


def _job_sample_from_report(
    report: JobReport,
    batch_entities: Dict[str, int],
) -> EntityJobSample:
    data = report.data if isinstance(report.data, dict) else {}
    entities_count = int(
        data.get("entities_count") or batch_entities.get(report.job_id, 0)
    )
    peak_rss = data.get("peak_rss_mb")
    return EntityJobSample(
        job_id=report.job_id,
        entities_count=entities_count,
        wall_sec=float(data.get("wall_sec") or 0.0),
        peak_rss_mb=float(peak_rss) if peak_rss is not None else None,
        success=report.success,
    )


__all__ = ["EntityExecutePipeline"]
