"""BacktestEngine facade — public entry for entity_based / slice_based backtest runs."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from core.modules.backtest_engine.core.shared.default_performance import (
    ENTITY_BASED_DEFAULT_PERFORMANCE,
    SLICE_BASED_DEFAULT_PERFORMANCE,
    merge_performance,
)
from core.modules.backtest_engine.core.shared.jobs import BacktestJob
from core.modules.backtest_engine.core.shared.types import ExecuteFn, JobReport, RunCallbacks
from core.modules.backtest_engine.core.slice_based.execute_pipeline import (
    SliceExecutePipeline,
)
from core.modules.backtest_engine.core.timeline_based.execute_pipeline import (
    TimelineExecutePipeline,
)

logger = logging.getLogger(__name__)


class BacktestEngine:
    """Backtest engine facade."""

    class Mode(str, Enum):
        """Backtest execution mode."""

        ENTITY_BASED = "entity_based"
        SLICE_BASED = "slice_based"

        @classmethod
        def normalize(cls, mode: str | BacktestEngine.Mode) -> str:
            if isinstance(mode, cls):
                return mode.value
            raw = str(mode or "").strip().lower()
            if raw == cls.ENTITY_BASED.value:
                return raw
            if raw == cls.SLICE_BASED.value:
                return raw
            raise ValueError(f"unknown backtest mode: {mode!r}")

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
                mode="slice_based",
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
            result: TimelineExecutePipeline.Result,
        ) -> BacktestEngine.RunResult:
            execution = result.execution
            return cls(
                mode="entity_based",
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
        ) -> BacktestEngine.RunResult:
            return BacktestEngine._run_entity_based(
                jobs,
                execute_fn,
                performance=performance,
                task_name=task_name,
                callbacks=callbacks,
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
        ) -> BacktestEngine.RunResult:
            return BacktestEngine._run_slice_based(
                jobs,
                execute_fn,
                performance=performance,
                task_name=task_name,
                callbacks=callbacks,
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
    ) -> BacktestEngine.RunResult:
        if jobs:
            BacktestJob.validate_many(jobs, mode=BacktestEngine.Mode.ENTITY_BASED)
        resolved_performance = merge_performance(
            ENTITY_BASED_DEFAULT_PERFORMANCE,
            performance,
        )
        resolved_callbacks = callbacks or RunCallbacks()
        label = task_name or "backtest"
        pipeline = TimelineExecutePipeline(log_label=label)
        pipeline_result = pipeline.run(
            jobs,
            resolved_performance,
            execute_fn=execute_fn,
            task_name=label,
            on_result=resolved_callbacks.on_result,
            on_release=resolved_callbacks.on_release,
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
    ) -> BacktestEngine.RunResult:
        if jobs:
            BacktestJob.validate_many(jobs, mode=BacktestEngine.Mode.SLICE_BASED)
        resolved_performance = merge_performance(
            SLICE_BASED_DEFAULT_PERFORMANCE,
            performance,
        )
        resolved_callbacks = callbacks or RunCallbacks()
        label = task_name or "backtest"
        pipeline = SliceExecutePipeline(log_label=label)
        pipeline_result = pipeline.run(
            jobs,
            resolved_performance,
            execute_fn=execute_fn,
            task_name=label,
            on_result=resolved_callbacks.on_result,
        )
        return BacktestEngine.RunResult.from_slice_based(pipeline_result)

    @classmethod
    def run(
        cls,
        mode: str | BacktestEngine.Mode,
        jobs: List[Dict[str, Any]],
        execute_fn: ExecuteFn,
        *,
        performance: Optional[Dict[str, Any]] = None,
        task_name: str = "",
        callbacks: Optional[RunCallbacks] = None,
    ) -> BacktestEngine.RunResult:
        normalized = cls.Mode.normalize(mode)
        if normalized == cls.Mode.ENTITY_BASED.value:
            return cls._run_entity_based(
                jobs,
                execute_fn,
                performance=performance,
                task_name=task_name,
                callbacks=callbacks,
            )
        if normalized == cls.Mode.SLICE_BASED.value:
            return cls._run_slice_based(
                jobs,
                execute_fn,
                performance=performance,
                task_name=task_name,
                callbacks=callbacks,
            )
        raise ValueError(f"unknown backtest mode: {mode!r}")


__all__ = ["BacktestEngine"]
