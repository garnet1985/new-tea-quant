"""BacktestEngine facade — schedule / timeline / performance entry."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.modules.backtest_engine.core.performance.settings import (
    resolve_entity_based_performance,
    resolve_slice_based_performance,
)
from core.modules.backtest_engine.core.schedule.entity_based.execute_pipeline import (
    EntityExecutePipeline,
)
from core.modules.backtest_engine.core.schedule.slice_based.execute_pipeline import (
    SliceExecutePipeline,
)
from core.modules.backtest_engine.core.shared.jobs import BacktestJob
from core.modules.backtest_engine.core.shared.modes import BacktestMode
from core.modules.backtest_engine.core.shared.types import ExecuteFn, JobReport, RunCallbacks
from core.modules.backtest_engine.core.timeline.timeline import Timeline, TimelineInput, TimelineWorkerExecute

logger = logging.getLogger(__name__)


class BacktestEngine:
    """Backtest engine facade（调度 / 时间推进 / 性能监控）。

    Timeline（探针前必须就绪；simulation window 必传）::

        run(start=, end=[, timeline=])  >  set_timeline(start=, end=[, timeline=])
        → 无 points 覆盖时按 window 调 CalendarService 建轴
        → window 必须落在 data.json 系统范围内

    主进程 SharedMemory 发布；worker ``Timeline.read_for_job`` + ``callbacks.on_tick``。
    ``on_tick`` 可选（缺省空转 + warning 一次）。
    """

    Mode = BacktestMode
    ExecuteFn = ExecuteFn
    RunCallbacks = RunCallbacks

    @classmethod
    def set_timeline(
        cls,
        timeline: TimelineInput = None,
        *,
        start: str = "",
        end: str = "",
    ) -> None:
        """注入 simulation window，并可选覆盖 points。须在 ``run`` / 探针前调用。"""
        Timeline.set(timeline, start=start, end=end)

    @classmethod
    def clear_timeline(cls) -> None:
        """清除 ``set_timeline`` 的 window / points 覆盖。"""
        Timeline.clear()

    @dataclass(frozen=True)
    class RunResult:
        mode: str
        success: bool
        total_jobs: int
        completed_jobs: int
        failed_jobs: int
        elapsed_seconds: float
        job_results: List[JobReport]
        plan: Any = None
        monitor_stats: Any = None
        pipeline_phases_sec: Optional[Dict[str, float]] = None

        @classmethod
        def from_slice_based(cls, result: SliceExecutePipeline.Result) -> BacktestEngine.RunResult:
            execution = result.execution
            phases = dict(getattr(result, "pipeline_phases_sec", None) or {})
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
                pipeline_phases_sec=phases or None,
            )

        @classmethod
        def from_entity_based(cls, result: EntityExecutePipeline.Result) -> BacktestEngine.RunResult:
            execution = result.execution
            phases = dict(getattr(result, "pipeline_phases_sec", None) or {})
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
                pipeline_phases_sec=phases or None,
            )

    class EntityBased:
        @staticmethod
        def run(
            jobs: List[Dict[str, Any]],
            *,
            start: str = "",
            end: str = "",
            timeline: TimelineInput = None,
            performance: Optional[Dict[str, Any]] = None,
            task_name: str = "",
            callbacks: Optional[RunCallbacks] = None,
            enable_progress_display: bool = True,
        ) -> BacktestEngine.RunResult:
            return BacktestEngine._run_entity_based(
                jobs,
                start=start,
                end=end,
                timeline=timeline,
                performance=performance,
                task_name=task_name,
                callbacks=callbacks,
                enable_progress_display=enable_progress_display,
            )

    class SliceBased:
        @staticmethod
        def run(
            jobs: List[Dict[str, Any]],
            *,
            start: str = "",
            end: str = "",
            timeline: TimelineInput = None,
            performance: Optional[Dict[str, Any]] = None,
            task_name: str = "",
            callbacks: Optional[RunCallbacks] = None,
            enable_progress_display: bool = True,
        ) -> BacktestEngine.RunResult:
            return BacktestEngine._run_slice_based(
                jobs,
                start=start,
                end=end,
                timeline=timeline,
                performance=performance,
                task_name=task_name,
                callbacks=callbacks,
                enable_progress_display=enable_progress_display,
            )

    entity_based = EntityBased
    slice_based = SliceBased

    @staticmethod
    def _prepare_jobs_timeline(
        jobs: List[Dict[str, Any]],
        *,
        start: str = "",
        end: str = "",
        timeline: TimelineInput = None,
    ) -> tuple[List[Dict[str, Any]], bool]:
        """探针前就绪 timeline。返回 (jobs, published)。无 jobs 时不发布。"""
        job_list = list(jobs or [])
        if not job_list:
            return job_list, False
        stamped, _effective = Timeline.begin_run(
            job_list,
            timeline,
            start=start,
            end=end,
        )
        return stamped, True

    @staticmethod
    def _run_entity_based(
        jobs: List[Dict[str, Any]],
        *,
        start: str = "",
        end: str = "",
        timeline: TimelineInput = None,
        performance: Optional[Dict[str, Any]] = None,
        task_name: str = "",
        callbacks: Optional[RunCallbacks] = None,
        enable_progress_display: bool = True,
    ) -> BacktestEngine.RunResult:
        resolved_callbacks = callbacks or RunCallbacks()
        published = False
        try:
            stamped_jobs, published = BacktestEngine._prepare_jobs_timeline(
                jobs,
                start=start,
                end=end,
                timeline=timeline,
            )
            worker_fn = TimelineWorkerExecute(resolved_callbacks)
            if stamped_jobs:
                BacktestJob.validate_many(stamped_jobs, mode=BacktestMode.ENTITY_BASED)
            resolved_performance = resolve_entity_based_performance(performance)
            label = task_name or "backtest"
            pipeline = EntityExecutePipeline(log_label=label)
            pipeline_result = pipeline.run(
                stamped_jobs,
                resolved_performance,
                execute_fn=worker_fn,
                task_name=label,
                on_before_all_tasks_start=resolved_callbacks.on_before_all_tasks_start,
                on_before_task_start=resolved_callbacks.on_before_task_start,
                on_after_task_complete=resolved_callbacks.on_after_task_complete,
                on_after_all_tasks_complete=resolved_callbacks.on_after_all_tasks_complete,
                on_task_result=resolved_callbacks.on_task_result,
                enable_progress_display=enable_progress_display,
            )
            return BacktestEngine.RunResult.from_entity_based(pipeline_result)
        finally:
            if published:
                Timeline.end_run()

    @staticmethod
    def _run_slice_based(
        jobs: List[Dict[str, Any]],
        *,
        start: str = "",
        end: str = "",
        timeline: TimelineInput = None,
        performance: Optional[Dict[str, Any]] = None,
        task_name: str = "",
        callbacks: Optional[RunCallbacks] = None,
        enable_progress_display: bool = True,
    ) -> BacktestEngine.RunResult:
        resolved_callbacks = callbacks or RunCallbacks()
        published = False
        try:
            stamped_jobs, published = BacktestEngine._prepare_jobs_timeline(
                jobs,
                start=start,
                end=end,
                timeline=timeline,
            )
            worker_fn = TimelineWorkerExecute(resolved_callbacks)
            if stamped_jobs:
                BacktestJob.validate_many(stamped_jobs, mode=BacktestMode.SLICE_BASED)
            resolved_performance = resolve_slice_based_performance(performance)
            label = task_name or "backtest"
            pipeline = SliceExecutePipeline(log_label=label)
            pipeline_result = pipeline.run(
                stamped_jobs,
                resolved_performance,
                execute_fn=worker_fn,
                task_name=label,
                on_before_all_tasks_start=resolved_callbacks.on_before_all_tasks_start,
                on_before_task_start=resolved_callbacks.on_before_task_start,
                on_after_task_complete=resolved_callbacks.on_after_task_complete,
                on_after_all_tasks_complete=resolved_callbacks.on_after_all_tasks_complete,
                on_task_result=resolved_callbacks.on_task_result,
                enable_progress_display=enable_progress_display,
            )
            return BacktestEngine.RunResult.from_slice_based(pipeline_result)
        finally:
            if published:
                Timeline.end_run()

    @classmethod
    def run(
        cls,
        mode: str | BacktestMode,
        jobs: List[Dict[str, Any]],
        *,
        start: str = "",
        end: str = "",
        timeline: TimelineInput = None,
        performance: Optional[Dict[str, Any]] = None,
        task_name: str = "",
        callbacks: Optional[RunCallbacks] = None,
        enable_progress_display: bool = True,
    ) -> BacktestEngine.RunResult:
        normalized = BacktestMode.normalize(mode)
        if normalized == BacktestMode.ENTITY_BASED.value:
            return cls._run_entity_based(
                jobs,
                start=start,
                end=end,
                timeline=timeline,
                performance=performance,
                task_name=task_name,
                callbacks=callbacks,
                enable_progress_display=enable_progress_display,
            )
        if normalized == BacktestMode.SLICE_BASED.value:
            return cls._run_slice_based(
                jobs,
                start=start,
                end=end,
                timeline=timeline,
                performance=performance,
                task_name=task_name,
                callbacks=callbacks,
                enable_progress_display=enable_progress_display,
            )
        raise ValueError(f"unknown backtest mode: {mode!r}")


__all__ = ["BacktestEngine"]
