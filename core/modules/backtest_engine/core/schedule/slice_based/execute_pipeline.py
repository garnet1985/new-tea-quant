"""Slice execute pipeline: skeleton plan → execute (head samples in-run) → refine."""
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
    JobReport,
    LoadPerEntityWindowFn,
    RunProgress,
    TaskCompleteFn,
    TaskStartFn,
)
from core.modules.backtest_engine.core.schedule.slice_based.executor import SliceExecutor
from core.modules.backtest_engine.core.schedule.slice_based.executor_duckdb import (
    SliceExecutorDuckDB,
)
from core.modules.backtest_engine.core.schedule.slice_based.monitor import (
    SliceMonitorConfig,
    SliceMonitorPlanSnapshot,
    SliceRunMonitor,
)
from core.modules.backtest_engine.core.shared.jobs import BacktestJob
from core.modules.backtest_engine.core.schedule.slice_based.planner import (
    SliceDispatchPlan,
    SliceJobBatch,
    SlicePlanner,
)
from core.modules.backtest_engine.core.schedule.slice_based.probe import SliceProbe

logger = logging.getLogger(__name__)


class SliceExecutePipeline:
    """End-to-end calendar-slice backtest: plan → execute → refine from head samples."""

    ExecuteFn = SliceExecutor.ExecuteFn
    OnResultHook = SliceExecutor.OnResultHook

    @dataclass(frozen=True)
    class Result:
        plan: SliceDispatchPlan
        batches: List[SliceJobBatch]
        monitor_config: SliceMonitorConfig
        execution: SliceExecutor.ExecutionResult
        monitor_stats: Any = None
        pipeline_phases_sec: Optional[Dict[str, float]] = None

    def __init__(self, *, log_label: str = "slice_based") -> None:
        self._log_label = log_label

    def run(
        self,
        jobs: List[Dict[str, Any]],
        performance: Dict[str, Any],
        *,
        execute_fn: SliceExecutor.ExecuteFn,
        task_name: str = "",
        on_before_all_tasks_start: Optional[Callable[[Any, List[Any]], None]] = None,
        on_before_task_start: Optional[TaskStartFn] = None,
        on_after_task_complete: Optional[TaskCompleteFn] = None,
        on_after_all_tasks_complete: Optional[Callable[[List[JobReport]], None]] = None,
        on_task_result: Optional[SliceExecutor.OnResultHook] = None,
        load_per_entity_window: Optional[LoadPerEntityWindowFn] = None,
        enable_progress_display: bool = True,
    ) -> SliceExecutePipeline.Result:
        label = task_name or self._log_label
        wall_t0 = time.perf_counter()
        phase_marks: Dict[str, float] = {"prep": wall_t0}
        progress = RunProgressReporter(
            task_name=label,
            run_mode=BacktestMode.SLICE_BASED.value,
            enable_progress_display=enable_progress_display,
        )
        progress.mark_phase(RunPhase.PREP)

        if jobs:
            BacktestJob.validate_many(jobs, mode=BacktestMode.SLICE_BASED)

        phase_marks["plan"] = time.perf_counter()
        progress.mark_phase(RunPhase.PLAN)
        plan, batches, monitor_config = SlicePlanner.plan_jobs(
            jobs,
            performance,
            execute_fn=execute_fn,
            log_label=self._log_label,
            load_per_entity_window=load_per_entity_window,
        )
        execute_units = plan.dispatch_jobs if plan.dispatch_jobs > 0 else len(batches)
        progress.set_execute_total(execute_units)

        if on_before_all_tasks_start is not None:
            try:
                on_before_all_tasks_start(plan, batches)
            except Exception as exc:
                logger.warning("on_before_all_tasks_start failed: %s", exc)

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

        def monitored_on_task_result(report: JobReport, run_progress: RunProgress) -> None:
            monitor.record_from_job_report(report)
            if on_task_result is not None:
                on_task_result(report, run_progress)

        phase_marks["execute"] = time.perf_counter()
        progress.mark_phase(RunPhase.EXECUTE)
        execution = SliceExecutorDuckDB.execute(
            plan,
            batches,
            context,
            execute_fn,
            on_result=monitored_on_task_result,
            on_before_task_start=on_before_task_start,
            on_after_task_complete=on_after_task_complete,
            log_label=self._log_label,
            progress_reporter=progress,
            load_per_entity_window=load_per_entity_window,
            duckdb_process_pool_scope=str(
                performance.get("duckdb_process_pool_scope", "auto")
            ),
            duckdb_resume_main_after_pool=bool(
                performance.get("duckdb_resume_main_after_pool", True)
            ),
        )
        monitor.flush()

        # Refine preload from head-slice samples embedded in execute results.
        probe_result = None
        for report in execution.job_results or []:
            if not report.success or not isinstance(report.data, dict):
                continue
            data = dict(report.data)
            if data.get("performance_metrics"):
                probe_result = SliceProbe.result_from_execute_report(
                    data, performance=performance
                )
                if probe_result.slices_sampled > 0:
                    break
                probe_result = None

        if probe_result is not None and probe_result.slices_sampled > 0:
            plan = SlicePlanner.refine_plan_from_probe(
                plan,
                probe_result,
                capacity,
                performance,
                log_label=self._log_label,
            )
            monitor_config = SlicePlanner._build_monitor(plan, performance)

        if on_after_all_tasks_complete is not None:
            try:
                on_after_all_tasks_complete(list(execution.job_results or []))
            except Exception as exc:
                logger.warning("on_after_all_tasks_complete failed: %s", exc)

        phase_marks["finish"] = time.perf_counter()
        progress.mark_phase(RunPhase.FINISH)
        wall_end = time.perf_counter()

        return SliceExecutePipeline.Result(
            plan=plan,
            batches=batches,
            monitor_config=monitor_config,
            execution=execution,
            monitor_stats=monitor.stats,
            pipeline_phases_sec=_pipeline_phases_sec(phase_marks, wall_end),
        )


def _pipeline_phases_sec(phase_marks: Dict[str, float], wall_end: float) -> Dict[str, float]:
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


__all__ = ["SliceExecutePipeline"]
