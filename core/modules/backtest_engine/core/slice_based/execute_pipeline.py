"""Slice execute pipeline: plan → monitor → subprocess orchestrator."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.modules.backtest_engine.core.shared.context import ExecutionContext
from core.infra.machine_capacity import MachineInfo
from core.modules.backtest_engine.core.shared.modes import BacktestMode
from core.modules.backtest_engine.core.shared.progress import RunPhase, RunProgressReporter
from core.modules.backtest_engine.core.shared.types import JobReport, RunProgress
from core.modules.backtest_engine.core.slice_based.executor import SliceExecutor
from core.modules.backtest_engine.core.slice_based.executor_duckdb import (
    SliceExecutorDuckDB,
)
from core.modules.backtest_engine.core.slice_based.monitor import (
    SliceMonitorConfig,
    SliceMonitorPlanSnapshot,
    SliceRunMonitor,
)
from core.modules.backtest_engine.core.shared.jobs import BacktestJob
from core.modules.backtest_engine.core.slice_based.planner import (
    SliceDispatchPlan,
    SliceJobBatch,
    SlicePlanner,
)

logger = logging.getLogger(__name__)


class SliceExecutePipeline:
    """End-to-end calendar-slice backtest: plan → monitor → execute."""

    ExecuteFn = SliceExecutor.ExecuteFn
    OnResultHook = SliceExecutor.OnResultHook

    @dataclass(frozen=True)
    class Result:
        plan: SliceDispatchPlan
        batches: List[SliceJobBatch]
        monitor_config: SliceMonitorConfig
        execution: SliceExecutor.ExecutionResult
        monitor_stats: Any = None

    def __init__(self, *, log_label: str = "slice_based") -> None:
        self._log_label = log_label

    def run(
        self,
        jobs: List[Dict[str, Any]],
        performance: Dict[str, Any],
        *,
        execute_fn: SliceExecutor.ExecuteFn,
        task_name: str = "",
        on_result: Optional[SliceExecutor.OnResultHook] = None,
        enable_progress_display: bool = True,
    ) -> SliceExecutePipeline.Result:
        label = task_name or self._log_label
        progress = RunProgressReporter(
            task_name=label,
            run_mode=BacktestMode.SLICE_BASED.value,
            enable_progress_display=enable_progress_display,
        )
        progress.mark_phase(RunPhase.PREP)

        if jobs:
            BacktestJob.validate_many(jobs, mode=BacktestMode.SLICE_BASED)

        progress.mark_phase(RunPhase.PLAN)
        plan, batches, monitor_config = SlicePlanner.plan_jobs(
            jobs,
            performance,
            execute_fn=execute_fn,
            log_label=self._log_label,
        )
        execute_units = plan.dispatch_jobs if plan.dispatch_jobs > 0 else len(batches)
        progress.set_execute_total(execute_units)

        capacity = MachineInfo.get_capacity(performance)
        available_memory_mb = MachineInfo.worker_pool_budget_mb(capacity)
        monitor = SliceRunMonitor(
            SliceMonitorPlanSnapshot(
                reader_workers=plan.reader_workers,
                queue_capacity=plan.queue_capacity,
                preload_depth=plan.preload_depth,
                slice_open_days=plan.slice_open_days,
                dispatch_slices=plan.dispatch_jobs,
                reader_memory_budget_mb=plan.reader_memory_budget_mb,
                compute_memory_budget_mb=plan.compute_memory_budget_mb,
                payload_memory_budget_mb=max(
                    1.0,
                    plan.memory_budget_mb
                    - plan.reader_memory_budget_mb
                    - plan.compute_memory_budget_mb,
                ),
                memory_budget_mb=plan.memory_budget_mb,
            ),
            monitor_config,
            available_memory_mb=available_memory_mb,
        )
        context = ExecutionContext.create(
            task_name=label,
            total_jobs=len(batches),
            executor="",
            performance=performance,
        )

        def monitored_on_result(report: JobReport, run_progress: RunProgress) -> None:
            monitor.record_from_job_report(report)
            if on_result is not None:
                on_result(report, run_progress)

        progress.mark_phase(RunPhase.EXECUTE)
        execution = SliceExecutorDuckDB.execute(
            plan,
            batches,
            context,
            execute_fn,
            on_result=monitored_on_result,
            log_label=self._log_label,
            progress_reporter=progress,
            duckdb_process_pool_scope=str(
                performance.get("duckdb_process_pool_scope", "auto")
            ),
            duckdb_resume_main_after_pool=bool(
                performance.get("duckdb_resume_main_after_pool", True)
            ),
        )
        monitor.flush()
        progress.mark_phase(RunPhase.FINISH)

        return SliceExecutePipeline.Result(
            plan=plan,
            batches=batches,
            monitor_config=monitor_config,
            execution=execution,
            monitor_stats=monitor.stats,
        )


__all__ = ["SliceExecutePipeline"]
