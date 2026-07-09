"""BacktestEngine facade — public entry for entity_based / slice_based backtest runs."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.modules.backtest_engine.core.shared.modes import BacktestMode
from core.modules.backtest_engine.core.shared.performance import (
    resolve_entity_based_performance,
    resolve_slice_based_performance,
)
from core.modules.backtest_engine.core.shared.jobs import BacktestJob
from core.modules.backtest_engine.core.shared.types import ExecuteFn, JobReport, RunCallbacks
from core.modules.backtest_engine.core.slice_based.execute_pipeline import (
    SliceExecutePipeline,
)
from core.modules.backtest_engine.core.entity_based.execute_pipeline import (
    EntityExecutePipeline,
)

logger = logging.getLogger(__name__)


class BacktestEngine:
    """Backtest engine facade."""

    Mode = BacktestMode

    ExecuteFn = ExecuteFn
    RunCallbacks = RunCallbacks

    @dataclass(frozen=True)
    class RunResult:
        """Stable run summary returned by BacktestEngine."""

        mode: str
        success: bool
        total_jobs: int
        completed_jobs: int
        failed_jobs: int
        elapsed_seconds: float
        job_results: List[JobReport]
        plan: Any = None
        monitor_stats: Any = None

        @classmethod
        def from_slice_based(
            cls,
            result: SliceExecutePipeline.Result,
        ) -> BacktestEngine.RunResult:
            execution = result.execution
            return cls(
                mode=BacktestMode.SLICE_BASED.value,
                success=execution.success,
                total_jobs=execution.total_jobs,
                completed_jobs=execution.completed_jobs,
                failed_jobs=execution.failed_jobs,
                elapsed_seconds=execution.elapsed_seconds,
                job_results=list(execution.job_results),
                plan=result.plan,
                monitor_stats=result.monitor_stats,
            )

        @classmethod
        def from_entity_based(
            cls,
            result: EntityExecutePipeline.Result,
        ) -> BacktestEngine.RunResult:
            execution = result.execution
            return cls(
                mode=BacktestMode.ENTITY_BASED.value,
                success=execution.success,
                total_jobs=execution.total_jobs,
                completed_jobs=execution.completed_jobs,
                failed_jobs=execution.failed_jobs,
                elapsed_seconds=execution.elapsed_seconds,
                job_results=list(execution.job_results),
                plan=result.plan,
                monitor_stats=result.monitor_stats,
            )

    class EntityBased:
        """entity_based API (entity-level jobs, process-pool QUEUE)."""

        @staticmethod
        def run(
            jobs: List[Dict[str, Any]],
            execute_fn: ExecuteFn,
            *,
            performance: Optional[Dict[str, Any]] = None,
            task_name: str = "",
            callbacks: Optional[RunCallbacks] = None,
            enable_progress_display: bool = True,
        ) -> BacktestEngine.RunResult:
            return BacktestEngine._run_entity_based(
                jobs,
                execute_fn,
                performance=performance,
                task_name=task_name,
                callbacks=callbacks,
                enable_progress_display=enable_progress_display,
            )

    class SliceBased:
        """slice_based API (calendar slice, bulk job + orchestrator)."""

        @staticmethod
        def run(
            jobs: List[Dict[str, Any]],
            execute_fn: ExecuteFn,
            *,
            performance: Optional[Dict[str, Any]] = None,
            task_name: str = "",
            callbacks: Optional[RunCallbacks] = None,
            enable_progress_display: bool = True,
        ) -> BacktestEngine.RunResult:
            return BacktestEngine._run_slice_based(
                jobs,
                execute_fn,
                performance=performance,
                task_name=task_name,
                callbacks=callbacks,
                enable_progress_display=enable_progress_display,
            )

    entity_based = EntityBased
    slice_based = SliceBased

    @staticmethod
    def _run_entity_based(
        jobs: List[Dict[str, Any]],
        execute_fn: ExecuteFn,
        *,
        performance: Optional[Dict[str, Any]] = None,
        task_name: str = "",
        callbacks: Optional[RunCallbacks] = None,
        enable_progress_display: bool = True,
    ) -> BacktestEngine.RunResult:
        if jobs:
            BacktestJob.validate_many(jobs, mode=BacktestMode.ENTITY_BASED)
        resolved_performance = resolve_entity_based_performance(performance)
        resolved_callbacks = callbacks or RunCallbacks()
        label = task_name or "backtest"
        pipeline = EntityExecutePipeline(log_label=label)
        pipeline_result = pipeline.run(
            jobs,
            resolved_performance,
            execute_fn=execute_fn,
            task_name=label,
            on_before_all_tasks_start=resolved_callbacks.on_before_all_tasks_start,
            on_child_process_task_start=resolved_callbacks.on_child_process_task_start,
            on_child_process_task_complete=resolved_callbacks.on_child_process_task_complete,
            on_after_all_tasks_complete=resolved_callbacks.on_after_all_tasks_complete,
            enable_progress_display=enable_progress_display,
        )
        return BacktestEngine.RunResult.from_entity_based(pipeline_result)

    @staticmethod
    def _run_slice_based(
        jobs: List[Dict[str, Any]],
        execute_fn: ExecuteFn,
        *,
        performance: Optional[Dict[str, Any]] = None,
        task_name: str = "",
        callbacks: Optional[RunCallbacks] = None,
        enable_progress_display: bool = True,
    ) -> BacktestEngine.RunResult:
        if jobs:
            BacktestJob.validate_many(jobs, mode=BacktestMode.SLICE_BASED)
        resolved_performance = resolve_slice_based_performance(performance)
        resolved_callbacks = callbacks or RunCallbacks()
        label = task_name or "backtest"
        pipeline = SliceExecutePipeline(log_label=label)
        pipeline_result = pipeline.run(
            jobs,
            resolved_performance,
            execute_fn=execute_fn,
            task_name=label,
            on_before_all_tasks_start=resolved_callbacks.on_before_all_tasks_start,
            on_child_process_task_start=resolved_callbacks.on_child_process_task_start,
            on_child_process_task_complete=resolved_callbacks.on_child_process_task_complete,
            on_after_all_tasks_complete=resolved_callbacks.on_after_all_tasks_complete,
            enable_progress_display=enable_progress_display,
        )
        return BacktestEngine.RunResult.from_slice_based(pipeline_result)

    @classmethod
    def run(
        cls,
        mode: str | BacktestMode,
        jobs: List[Dict[str, Any]],
        execute_fn: ExecuteFn,
        *,
        performance: Optional[Dict[str, Any]] = None,
        task_name: str = "",
        callbacks: Optional[RunCallbacks] = None,
        enable_progress_display: bool = True,
    ) -> BacktestEngine.RunResult:
        normalized = BacktestMode.normalize(mode)
        if normalized == BacktestMode.ENTITY_BASED.value:
            return cls._run_entity_based(
                jobs,
                execute_fn,
                performance=performance,
                task_name=task_name,
                callbacks=callbacks,
                enable_progress_display=enable_progress_display,
            )
        if normalized == BacktestMode.SLICE_BASED.value:
            return cls._run_slice_based(
                jobs,
                execute_fn,
                performance=performance,
                task_name=task_name,
                callbacks=callbacks,
                enable_progress_display=enable_progress_display,
            )
        raise ValueError(f"unknown backtest mode: {mode!r}")


__all__ = ["BacktestEngine"]
