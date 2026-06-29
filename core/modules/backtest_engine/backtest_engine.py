"""BacktestEngine facade — public entry for timeline / sliced backtest runs."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from core.modules.backtest_engine.core.shared.types import ExecuteFn, JobReport
from core.modules.backtest_engine.core.timeline_based.config import TimelineConfig
from core.modules.backtest_engine.core.timeline_based.execute_pipeline import (
    TimelineExecutePipeline,
)
from core.modules.backtest_engine.core.timeline_based.executor import TimelineExecutor

logger = logging.getLogger(__name__)


class BacktestEngine:
    """
    Backtest engine facade.

    Public surface: ``BacktestEngine`` and nested ``Timeline`` / ``RunResult``.
    Internal modules export one class each (e.g. ``TimelineExecutor``).
    """

    ExecuteFn = ExecuteFn
    OnResultHook = TimelineExecutor.OnResultHook
    OnReleaseHook = TimelineExecutor.OnReleaseHook

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
        def from_timeline(
            cls,
            result: TimelineExecutePipeline.Result,
        ) -> BacktestEngine.RunResult:
            execution = result.execution
            return cls(
                mode="timeline",
                success=execution.success,
                total_jobs=execution.total_jobs,
                completed_jobs=execution.completed_jobs,
                failed_jobs=execution.failed_jobs,
                elapsed_seconds=execution.elapsed_seconds,
                job_results=list(execution.job_results),
                plan=result.plan,
                monitor_stats=result.monitor_stats,
            )

    class Timeline:
        """Timeline backtest API (entity-level jobs, process-pool QUEUE)."""

        @staticmethod
        def run(
            jobs: List[Dict[str, Any]],
            execute_fn: ExecuteFn,
            *,
            executor_key: str,
            run_name: str = "",
            on_result: Optional[BacktestEngine.OnResultHook] = None,
            on_release: Optional[BacktestEngine.OnReleaseHook] = None,
            data_mgr: Optional[Any] = None,
            log_label: str = "backtest",
        ) -> BacktestEngine.RunResult:
            performance = TimelineConfig.resolve_dispatch_performance(executor_key)
            pipeline = TimelineExecutePipeline(log_label=log_label)
            pipeline_result = pipeline.run(
                jobs,
                performance,
                execute_fn=execute_fn,
                executor_key=executor_key,
                run_name=run_name or log_label,
                on_result=on_result,
                on_release=on_release,
                data_mgr=data_mgr,
            )
            return BacktestEngine.RunResult.from_timeline(pipeline_result)

    class Sliced:
        """Sliced backtest API (calendar slice, reader + compute)."""

        @staticmethod
        def run(
            jobs: List[Dict[str, Any]],
            execute_fn: ExecuteFn,
            *,
            executor_key: str,
            **kwargs: Any,
        ) -> BacktestEngine.RunResult:
            raise NotImplementedError(
                "sliced mode is not wired to BacktestEngine yet; use timeline mode"
            )

    timeline = Timeline
    sliced = Sliced

    @classmethod
    def run(
        cls,
        *,
        mode: str,
        jobs: List[Dict[str, Any]],
        execute_fn: ExecuteFn,
        executor_key: str,
        **kwargs: Any,
    ) -> BacktestEngine.RunResult:
        normalized = str(mode or "").strip().lower()
        if normalized == "timeline":
            return cls.timeline.run(
                jobs,
                execute_fn,
                executor_key=executor_key,
                **kwargs,
            )
        if normalized == "sliced":
            return cls.sliced.run(
                jobs,
                execute_fn,
                executor_key=executor_key,
                **kwargs,
            )
        raise ValueError(f"unknown backtest mode: {mode!r}")


__all__ = ["BacktestEngine"]
